#!/usr/bin/env python
# coding: utf-8

# In[270]:


# ##############################################################################################
# IMPORT PACKAGES AND SET DATA SOURCES
##############################################################################################

#import packages
import pickle
from os.path import join as opj
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, MultiPoint, Polygon, MultiPolygon
from shapely.ops import cascaded_union
import matplotlib.pyplot as plt
# get_ipython().run_line_magic('matplotlib', 'inline')
from mpl_toolkits.axes_grid1 import make_axes_locatable
from shapely.ops import nearest_points
import cvxpy as cp

# SERVER DATA DIR
DATA_DIR = "data"

SUBSET = False
# if True, run on "BIG ZONES", if False, runs on "SMALL ZONES"
# In[271]:


def Haversine(lat1, lon1, lat2, lon2):
	"""
	Calculate the Great Circle distance on Earth between two latitude-longitude
	points
	:param lat1 Latitude of Point 1 in degrees
	:param lon1 Longtiude of Point 1 in degrees
	:param lat2 Latitude of Point 2 in degrees
	:param lon2 Longtiude of Point 2 in degrees
	:returns Distance between the two points in kilometres
	"""
	Rearth = 6371
	lat1   = np.radians(lat1)
	lon1   = np.radians(lon1)
	lat2   = np.radians(lat2)
	lon2   = np.radians(lon2)
	#Haversine formula
	dlon = lon2 - lon1
	dlat = lat2 - lat1
	a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
	c = 2 * np.arcsin(np.sqrt(a))
	return Rearth*c


# In[272]:


def Distance(loc1, loc2):
	# print(loc1.x, loc1.y, loc2.x, loc2.y)
	return Haversine(loc1.y, loc1.x, loc2.y, loc2.x)


# In[273]:


def Fetch(df, key_col, key, value):
	#counties['disposal'].loc[counties['COUNTY']=='San Diego'].values[0]
	return df[value].loc[df[key_col]==key].values[0]


# In[274]:


def SaveBuildVars(build):
	"""
	Takes the output (build) of the optimization function and saves the values as a dict
	:returns build_out dict.
	"""
	build_out = {}
	for zone in build.keys():
		#print("ZONE: ", zone)
		build_out[zone] = {}
		build_out[zone]['IndF'] = build[zone]['IndF']['qb'].value
		build_out[zone]['OnfarmF'] = build[zone]['OnfarmF']['qb'].value
		build_out[zone]['CommF']=build[zone]['CommF']['qb'].value
	#print("DONE with loop")
	# can also ask to save to pickle file here if we want?
	return build_out


# In[275]:

# if doing subset, use BIG ZONES
if SUBSET == True:
		testzones_shapefile = "big_zones/big_zones.shp"
# else, use our SMALL ZONES
else:
	testzones_shapefile = "sites/smallzones.shp"

# read in
testzones = gpd.read_file(opj(DATA_DIR,
								testzones_shapefile))
# make sure in correct (degrees-based) CRS
testzones2 = testzones.to_crs("EPSG:4326")
# create centroid geometry
testzones2['centroid'] = testzones2['geometry'].centroid
# create new attribute (zoneid) from index
testzones2['zoneid'] = testzones2.index

# rename for use in 
testzones = testzones2
#weird things had happened with the crs, this mess should be fixing it!
# testzones

# replace NaN w zero for zones without any rangeland area (only needed for SMALL ZONES)
if SUBSET == False:
	testzones['rangeland_']=testzones['rangeland_'].fillna(0)

# In[276]:


###VARIABLES###

waste_to_compost = 0.58 #% volume change from waste to compost

roademissionscollect=0.22
roademissionshaul=0.22

izcollect=0.15
izhaul=0.15

roadcost=0.35

industrialmax=1000000
onfarmmax=100000
communitymax=10000

ifco_emiss = 30
ofco_emiss = 1
comco_emiss = .5

ifpro_emiss = 18
ofpro_emiss = 7
compro_emiss = .5

emiss_spread=1.08
emiss_landfill=-183


ifcost = 200
ofcost = 50
comcost = 10

seqfact=-100000


# In[277]:

# SETS: 

ftype=['IndF', 'OnfarmF', 'CommF'] #facility types

build = {} #decision variable dictionary for build

flow = {} #decision variable dictionary for material flow

for zone in testzones['zoneid']:
	# print("FIRST ZONE: ", zone)
	build[zone]={}
	#print(z1loc)
	for f in ftype:
		build[zone][f]={}
		#first decicion variable: how much (tons) to build per zone per type
		build[zone][f]['qb']=cp.Variable()

for zone in testzones['zoneid']:
	z1loc=Fetch(testzones, 'zoneid', zone, 'centroid')
	flow[zone] = {}
	for zone2 in testzones['zoneid']:
		# open new dictionary entry for saving between zone things
		flow[zone][zone2]= {}
		#second decision variable: C flow from feedstock source in zone to build in a zone (zone or diff)
		#for now not distinguishing by type, but could add this in later!!
		flow[zone][zone2]['qc']=cp.Variable()
		#third decision variable: L flow from a build in a zone to a land in a second zone (same or diff)
		flow[zone][zone2]['ql']=cp.Variable()
		

		#grab second zone location for calculating distance
		z2loc=Fetch(testzones, 'zoneid', zone2, 'centroid')
		# calculate distance between all zones
		dist=Distance(z1loc, z2loc)

		# in objective function, the following will get multiplied by the variables (qc & ql) above.
		if zone==zone2: #dist equals zero, so multiply by intrazone assumption
			flow[zone][zone2]['collectemissions']=izcollect*1.4*roademissionscollect #kgC02/ton
			# print(build[zone][zone2]['collectemissions'])
			flow[zone][zone2]['haulemissions']=izhaul*1.4*roademissionshaul
			# print(build[zone][zone2]['haulemissions'])
			flow[zone][zone2]['transcost']=izcollect*1.4*roadcost
		else:
			# if zones are different, grab the real distance between centroids
			flow[zone][zone2]['collectemissions']=dist*1.4*roademissionscollect
			flow[zone][zone2]['haulemissions']=dist*1.4*roademissionshaul
			flow[zone][zone2]['transcost']=dist*1.4*roadcost
		print("DIST: ", dist)


# print (build)

print("decision variables defined")        


# In[278]:


###building the objective function: EMISSIONS ###
obj=0

## collection and hauling emissions###
for zone in testzones['zoneid']:
	#print(zone) 
	for zone2 in testzones['zoneid']:
		# print(zone2)
		zz = flow[zone][zone2]
		# CE = int(zz['collectemissions'])+1
		obj += zz['qc'] * zz['collectemissions']
		obj += zz['ql'] * zz['haulemissions'] 


###construction and processing emissions### 
for zone in testzones['zoneid']:
	#print(zone)
	for f in ftype:
		#print(f)
		x=build[zone][f]['qb']  
		if f == 'IndF':
			obj+= x*ifco_emiss
			obj+= x*ifpro_emiss
		elif f=='OnfarmF':
			obj+= x*ofco_emiss
			obj+= x*ofpro_emiss
		elif f=='CommF':
			obj+= x*comco_emiss
			obj+= x*compro_emiss


######spreading, avoided landfill emissions and sequestration benefit ### 
for zone in testzones['zoneid']:
	#print(z1area)
	for zone2 in testzones['zoneid']:
		zz = flow[zone][zone2]
		
		#avoided landfill emissions (no longer staying in county, now going to facility)
		obj += zz['qc']*emiss_landfill
		
#         spreading emissions (where emiss_spread is in kgco2/ton)
		obj += zz['ql']*emiss_spread
		
#         sequestration benefit (where seqfact is kgco2e/ton)
		obj += zz['ql']*seqfact
		
# print(obj)
print("objective factor (mostly) defined")


# In[279]:


###defining constraints###
cons=[]

##supply constraint###
for zone in testzones['zoneid']:
	#grab total avaialble feedstock per zone
	z1msw=Fetch(testzones, 'zoneid', zone, 'msw_sum')
#     print("available feedstock: ", z1msw)
	temp_supply=0
	for zone2 in testzones['zoneid']:
		temp_supply += flow[zone][zone2]['qc']
	# the amount you're sending out to all zones must be less than the feedstock available in initial zone
	cons+=[temp_supply<=z1msw]

	
# ### land constraint###
for zone2 in testzones['zoneid']:
	#grab land area per zone
	if SUBSET == True:
		z2area=Fetch(testzones, 'zoneid', zone2, 'Shape_Area')
	else:
		z2area=Fetch(testzones, 'zoneid', zone2, 'rangeland_')
	#TODO- make sure column names are consistent between small and big zones
#     print("available land area: ", z2area)
	temp_apply=0
	for zone in testzones['zoneid']:
		temp_apply += flow[zone][zone2]['ql']
	cons+=[temp_apply<=z2area]
	

# ###facility type###
for zone in testzones['zoneid']:
	for f in ftype:
		if f == 'IndF':
			cons+=[build[zone][f]['qb']<=industrialmax]
			
		elif f == 'OnfarmF':
			cons+=[build[zone][f]['qb']<=onfarmmax]
			
		elif f == 'CommF':
			cons+=[build[zone][f]['qb']<=communitymax]
			
			
# ### build corresponds to flow in (and out???) ###
for zone in testzones['zoneid']:
	temp_build = 0
	temp_inflow = 0
	temp_outflow = 0
	# sum all build type quantities in this zone
	for f in ftype:
		temp_build += build[zone][f]['qb']
	# now go through all the zones and sum up how much is being sent to this zone
	for zone2 in testzones['zoneid']:
		temp_inflow += flow[zone2][zone]['qc']
#     print("ZONE: ", zone, "-- BUILD: ", temp_build, "-- INFLOW: ", temp_inflow, ".")
	for zone_land in testzones['zoneid']:
		temp_outflow += flow[zone][zone_land]['ql']
	#these need to be balanced!
	cons+=[temp_build>=temp_inflow]
	# cannot strand compost at facility!
	cons+=[temp_inflow == waste_to_compost * temp_outflow]

for zone in testzones['zoneid']:
	for zone2 in testzones['zoneid']:
		cons += [flow[zone][zone2]['qc']>=0]
		cons += [flow[zone][zone2]['ql']>=0]

# In[280]:


###define the problem###

prob = cp.Problem(cp.Minimize(obj), cons)

val = prob.solve(verbose = True)

print("VALUE: ", val, "(kgCO2e")


# In[282]:


###printing the build size###

for zone in build.keys():

	indf=build[zone]['IndF']['qb'].value
	onfarm=build[zone]['OnfarmF']['qb'].value
	community=build[zone]['CommF']['qb'].value
	print('Industrial', indf, 'On-farm', onfarm, 'Community', community)

for zone in flow.keys():
	print("START ZONE: ", zone)
	for zone2 in flow[zone].keys():
		print("**END ZONE: ", zone2)
		print(">>>>QC: ", flow[zone][zone2]['qc'].value)
		print(">>>>QL: ", flow[zone][zone2]['ql'].value)


# In[ ]:


# SaveBuildVars(build)

