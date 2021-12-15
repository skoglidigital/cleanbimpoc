# Hello streamlit
import streamlit as st
import pandas as pd
import numpy as np
import base64
import io

# ifcopenshell
import ifcopenshell
from ifcopenshell.util import element

st.title("Hello Renholdskalkulator")
st.text("Last opp P13 kompatibel BIM og din renholdskost per m2 i menyen til venstre")

# file uploader
st.sidebar.header("BIM-basert renholdskostnader")
st.sidebar.caption("Sett inn kostnader per m2 i kr")
your_m2_price = st.sidebar.number_input("Sett inn din pris per m2",min_value=0,step = 100)
st.sidebar.caption("Last opp en renholdskompatibel ifc")
uploaded_file = st.sidebar.file_uploader("Choose a file",type=["ifc"])


## If/when we want to test agains P13 mvd it is found here:
## https://test-bimvalbygg.dibk.no/mvd/ramme_etttrinn_igangsetting.mvdxml

# Loads a data from a string representation of an IFC file
# ref: https://community.osarch.org/discussion/659/ifcopenshell-how-to-work-with-file-content-instead-of-file-path
def load_ifc(ifc_file):
	ifc = ifcopenshell.file.from_string(ifc_file)
	return ifc
def get_qtos(elem):
    psets = element.get_psets(elem)
    if "BaseQuantities" in psets:
        return psets["BaseQuantities"]
    else:
        return {}
# Fetched from ifcopenshell.util.unit --> will be part of newer releases
def get_unit_assignment(ifc_file):
    unit_assignments = ifc_file.by_type("IfcUnitAssignment")
    if unit_assignments:
        return unit_assignments[0]

# function to get net areas for spaces
def get_net_areas(elem):
    qtos=get_qtos(elem)
    net_areas = {}
    if "NetFloorArea" in qtos:
        net_areas["Netto Gulvareal m2"] = round(qtos["NetFloorArea"],2)
    else:
        net_areas["Netto Gulvareal m2"] = None
    if "NetCeilingArea" in qtos:
        net_areas["Netto Takareal m2"] = round(qtos["NetCeilingArea"],2)
    else:
        net_areas["Netto Takareal m2"] = None
    if "NetWallArea" in qtos:
        net_areas["Netto Veggareal m2"] = round(qtos["NetWallArea"],2)
    else:
        net_areas["Netto Veggareal m2"] = None
    return net_areas

def get_room_info(space):
    room = space.get_info()
    info_to_return = {}

    # Name
    if "Name" in room:
        info_to_return["Navn"] = room["Name"]
    else:
        info_to_return["Navn"] = None
    # LongName
    if "LongName" in room:
        info_to_return["Langt navn"] = room["LongName"]
    else:
        info_to_return["Langt navn"] = None
    # Type
    spaceType = element.get_type(space)
    if spaceType:
        info_to_return["Romtype"] = spaceType.Name
    else:
        info_to_return["Romtype"] = None
    # GlobalID
    if "GlobalId" in room:
        info_to_return["GlobalId"] = room["GlobalId"]
    else:
        info_to_return["GlobalId"] = None

    # add qtos
    info_to_return.update(get_net_areas(space))

    return info_to_return

def space_df(spaces,options):
    spacelist = []
    for space in spaces:
        spacelist.append(get_room_info(space))
    df = pd.DataFrame(spacelist)
    if len(options) >0:
        return df[df["Romtype"].isin(options)]
    else:
        return df
# Function to get rooms, id, name, longname, net_areas and return pandas

def get_cost_df(df,cost_m2):
    df["Gulv kr"] = df["Netto Gulvareal m2"]*cost_m2
    df["Tak kr"] = df["Netto Takareal m2"]*cost_m2
    df["Vegger kr"] = df["Netto Veggareal m2"]*cost_m2
    return df

# Used to fetch gross area on buildng
def get_bruttoareal(elem):
    qtos=get_qtos(elem)
    if "GrossFloorArea" in qtos:
        return round(qtos["GrossFloorArea"],2)

def get_table_download_link(df):
    """Generates a link allowing the data in a given panda dataframe to be downloaded
    in:  dataframe
    out: href string
    """
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()  # some strings <-> bytes conversions necessary here
    href = f'<a download="renholdskostnader.csv" href="data:file/csv;base64,{b64}">Last ned regneark</a>'
    return href

if uploaded_file is not None:

     stringio = io.StringIO(uploaded_file.read().decode("utf-8"))
     #st.write(stringio)

     # To read file as string:
     string_data = stringio.read()

     # Load in the ifc file
     file = load_ifc(string_data)
     st.sidebar.caption("IFC versjon: {}".format(file.schema))

     # print ut antall rom og lagre rom i liste
     spaces = file.by_type("IfcSpace")
     st.write("Antall rom totalt i modell: {}".format(len(spaces)))

     # Get and write out some info on the building
     building = file.by_type("IfcBuilding")[0]
     if building != None:
         st.sidebar.header("Bygning: {}".format(building.Name))
         st.sidebar.text("Bruttoareal: {} m2".format(get_bruttoareal(building)))
     # Assumes SI units for this PoC. Add more unit intelligence later
     #st.write(get_unit_assignment(file).Units)
     # Get and write out some info on the site
     site = file.by_type("IfcSite")[0]

     if site.SiteAddress:
         st.sidebar.text("Adresse: {}".format(site.SiteAddress.AddressLines[0]))
         st.sidebar.text("Postkode: {}, Sted: {}".format(site.SiteAddress.PostalCode,site.SiteAddress.Town))
         st.sidebar.text("Matrikkelnummer: {}".format(site.LandTitleNumber))
     if your_m2_price is not None:
         ### Main (?)
         spaceTypes = file.by_type("IfcSpaceType")
         spaceTypeCategories = []
         for spaceType in spaceTypes:
             spaceTypeCategories.append(spaceType.Name)

         options = st.multiselect('Hvilke romtyper?',
             spaceTypeCategories,default = spaceTypeCategories)

         df = space_df(spaces,options)

         # print out spacelist DataFrame

         st.dataframe(get_cost_df(df,your_m2_price))

         st.subheader("Totale renholdskostnader:")
         st.text("Gulv: {:.2f} kr".format(df["Gulv kr"].sum()))
         st.text("Tak: {:.2f} kr".format(df["Tak kr"].sum()))
         st.text("Vegger: {:.2f} kr".format(df["Vegger kr"].sum()))

         st.markdown(get_table_download_link(df), unsafe_allow_html=True)
