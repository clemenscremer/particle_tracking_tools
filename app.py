import streamlit as st

import mikeio
import pandas as pd
import numpy as np

from pyproj import Transformer
import plotly.express as px
from streamlit_plotly_events import plotly_events
#from streamlit_plotly_mapbox_events import plotly_mapbox_events # for selection from map
from streamlit_folium import st_folium
import folium

# get data
xmlname = './data/particles.xml'

# functions
@st.cache()
def read_track(xmlname):
    df = pd.read_xml(xmlname, encoding="US-ASCII", xpath="//Particle")

    #expand particle attributes in DataFrame
    df[['x', 'y', 'z', 'age', 'hdir', 'hspeed', 'vspeed', 'mass']] = df['Particle'].str.split(',', expand=True)
    df.drop(columns='Particle', inplace=True)
    s = df.select_dtypes(include='object').columns
    df[s] = df[s].astype("float")

    # for dynamic plotting: aggregate in intervals by just ceiling to 10 min. intervals, then revert back to minutes
    df['minutes*10'] = df.age.apply(lambda x: np.ceil(x/600))
    df['minutes'] = df.age.apply(lambda x: np.ceil(x/60))

    transformer = Transformer.from_crs("epsg:25832", "epsg:4326")
    xt, yt = transformer.transform(df['x'], df['y'])
    df['lat'], df['lon'] = xt, yt
    lat_center, lon_center = df.lat.mean(), df.lon.mean()

    return df, lat_center, lon_center 

@st.cache()
def animated_plot(df, anim=None):
    # show dynamic figure
    fig = px.density_mapbox(df, lat='lat', lon='lon', radius=5,
                            center=dict(lat=lat_center, lon=lon_center), zoom=11,
                            mapbox_style="carto-positron",#"open-street-map", 
                            animation_frame='minutes*10', animation_group='minutes*10', 
                            opacity=0.8,
                            hover_data=["hspeed"])
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

@st.cache()
def tide_plot(df):
    # grouped plot (of z=tide) for selection 
    df_grouped = df.groupby('minutes').mean().z
    fig2 = px.line(df_grouped, x=df_grouped.index, y="z")
    return fig2


# retrieve data (particle track)
df, lat_center, lon_center = read_track(xmlname)



# main page
st.header("Particle Tracking Demo")
st.markdown("This app exemplarily shows the release of particles (around timestep 0) and their subsequent movement with the flow of the Elbe river. Particles are released in a 30 m x 30 m area.")
st.markdown("-----")

st.subheader("Location and type of incident")
# map for selection of injection point coordinates
sel_map = folium.Map(location = [53.54216926197158, 9.929960125085614], zoom_start=11)
map_data = st_folium(sel_map, width=725)
sel_coords = map_data["last_clicked"]


try:
    sel_x, sel_y = sel_coords["lat"], sel_coords["lng"]
    st.write(f"Selected point for particle injection: {sel_x}, {sel_y}")
except TypeError:
    st.write(f"Please select a point for particle injection.")



st.markdown("-----")
st.subheader("Results")
tab1, tab2 = st.tabs(["Manual selection", "Animated"])
# tab with manual selection
ts_selection = st.sidebar.radio("Manual timestep selection:", ["Hover", "Click"])
with tab1:
    st.write("**Manually select timestep** from graph below. Either by hovering or by clicking (see switch in the sidebar).")
    if ts_selection == "Hover":
        hover_event = True
        click_event = False
    else:
        hover_event = False
        click_event = True

    # do tidal plot (from floating particle z)   
    fig2 = tide_plot(df)
    # bidirectional communication on fig2 via plotly events
    selected_time = plotly_events(fig2, click_event=click_event, hover_event=hover_event)


    # just for debugging
    #st.write(selected_points)
    try:
        selected_ts = selected_time[0]["x"]
    except IndexError:
        selected_ts = 0

    st.markdown("**Map of particle distribution**")
    st.write(f"selected timestep: {selected_ts} minutes after particle injection")


    # map at selected timestep
    df_t = df[df['minutes']== selected_ts]
    # ToDO: move to function with / without animation
    fig3 = px.density_mapbox(df_t, lat='lat', lon='lon', radius=5,
                            center=dict(lat=lat_center, lon=lon_center), zoom=11,
                            mapbox_style="carto-positron",#"open-street-map", 
                            opacity=0.8,
                            hover_data=["hspeed"])
    fig3.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    st.write(fig3)

# animation tab
with tab2: 
    st.write("Animated particle track")
    fig = animated_plot(df)
    st.write(fig)



# sidebar / settings
with st.sidebar.expander("Particle release (not implemented)"):
    

    st.markdown("injection coordinates (*picking from map should also be an option*")
    xsb, ysb = lat_center, lon_center
    #xsb, ysb = sel_x, sel_y # take from map

    st.number_input("latitude: ",value = xsb)
    st.number_input("longitude: ",value = ysb)

    st.selectbox("uncertainty in release location", ('1 m', '10 m', '50 m', '100 m'))
    st.selectbox("uncertainty in release time", ('1 min', '10 min', '60 min'))
    particle_type = st.select_slider("type of particle", ["Person", "Contaminant"])
    if particle_type == "Person":
        st.markdown("Person attributes")
        particle_activity = st.select_slider("active/passive", ["passive", "active"]) 
        st.selectbox("Person", ('child', 'average'))

    else:
        particle_activity = "passive" # this could determine dispersion ~= swimming
        st.markdown("**Contaminant attributes**")
        st.selectbox("Contaminant", ('oil', 'fat', 'miscible'))

