import streamlit as st

import mikeio
import pandas as pd
import numpy as np

from pyproj import Transformer
import plotly.express as px
from streamlit_plotly_events import plotly_events

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
def animated_plot(df):
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


# page
st.header("Particle Tracking Demo")

ts_selection = st.sidebar.radio("Timestep selection:", ["Hover", "Click"])

tab1, tab2 = st.tabs(["Manual selection", "Animated"])
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
    selected_points = plotly_events(fig2, click_event=click_event, hover_event=hover_event)


    # just for debugging
    #st.write(selected_points)
    try:
        selected_ts = selected_points[0]["x"]
    except IndexError:
        selected_ts = 0

    st.write(f"selected timestep: {selected_ts} minutes after particle injection")


    # map at selected timestep
    df_t = df[df['minutes']== selected_ts]
    fig3 = px.density_mapbox(df_t, lat='lat', lon='lon', radius=5,

                            center=dict(lat=lat_center, lon=lon_center), zoom=11,
                            mapbox_style="carto-positron",#"open-street-map", 
                            opacity=0.8,
                            hover_data=["hspeed"])
    fig3.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.write(fig3)

with tab2: 
    st.write("Animated particle track")
    fig = animated_plot(df)
    st.write(fig)