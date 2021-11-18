# model_v1.py


import pickle
import cvxpy as cp
import pandas
import geopandas as gpd
import numpy as np
import os 
from os.path import join as opj

DATA_DIR = "data"

### functions used in this script ###
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

def Distance(loc1, loc2):
	# print(loc1.x, loc1.y, loc2.x, loc2.y)
	return Haversine(loc1.y, loc1.x, loc2.y, loc2.x)

def Fetch(df, key_col, key, value):
	#counties['disposal'].loc[counties['COUNTY']=='San Diego'].values[0]
	return df[value].loc[df[key_col]==key].values[0]

def SaveBuildVars(build):
	"""
	Takes the output (build) of the optimization function and saves the values as a dict
	:returns build_out dict.
	"""

	build_out = {}

	for zone in build.keys():
		# print("ZONE: ", zone)
		build_out[zone] = {}
		build_out[zone]['IndF'] = build[zone]['IndF']['q'].value
		build_out[zone]['OnfarmF'] = build[zone]['OnfarmF']['q'].value
		build_out[zone]['CommF']=build[zone]['CommF']['q'].value
	# print("DONE with loop")
	# can also ask to save to pickle file here if we want?
	return build_out


### LOAD DATA ###
testzones_shapefile = "big_zones/big_zones.shp"
testzones = gpd.read_file(opj(DATA_DIR, testzones_shapefile))

testzones['centroid'] = testzones['geometry'].centroid
testzones['zoneid'] = testzones.index

###VARIABLES###

roademissionscollect = 30 
roademissionshaul =30 
roadcost=60

izcollect = 1
izhaul = 1

industrialmax=100000
onfarmmax=10000
communitymax=1000

seqfact=-100

ftype=['IndF', 'OnfarmF', 'CommF'] #facility types

build={} #decision variable dictionary

for zone in range(len(testzones)):
	build[zone]={}
	z1loc=Fetch(testzones, 'zoneid', zone, 'centroid')
	#print(z1loc)
	for f in ftype:
		build[zone][f]={}
		build[zone][f]['q']=cp.Variable()
	for zone2 in range(len(testzones)):
		z2loc=Fetch(testzones, 'zoneid', zone2, 'centroid')
		dist=Distance(z1loc, z2loc)
		build[zone][zone2]={}
		if zone==zone2:
			build[zone][zone2]['collectemissions']=izcollect*1.4*roademissionscollect
			build[zone][zone2]['haulemissions']=izhaul*1.4*roademissionshaul	
		else:
			build[zone][zone2]['collectemissions']=dist*1.4*roademissionscollect
			build[zone][zone2]['haulemissions']=dist*1.4*roademissionshaul

		build[zone][zone2]['transcost']=dist*1.4*roadcost
		#separate collection and hauling emissions and costs
		#print(dist)
		#print (zone, f)

# print (build)


###building the objective function###
obj=0

###collection emissions###
for zone in testzones['zoneid']:
	#print(zone)
	for f in ftype:
		#print(f)
		x=build[zone][f]['q']  
		for zone2 in testzones['zoneid']:
			#print(zone2)
			y=build[zone][zone2]['collectemissions']    
		obj+= x*y

###hauling emissions### 
for zone in testzones['zoneid']:
	#print(zone)
	for f in ftype:
		#print(f)
		x=build[zone][f]['q']  
		for zone2 in testzones['zoneid']:
			#print(zone2)
			y=build[zone][zone2]['haulemissions']    
		obj+= x*y

###sequestration benefit###
for zone in testzones['zoneid']:
	z1area=Fetch(testzones, 'zoneid', zone, 'Shape_Area')
	print(z1area)
	temp=0
	for f in ftype:
		temp+= build[zone][f]['q']
		
	obj+= temp*z1area*seqfact

# print(obj)            

###defining constraints###
cons=[]

###supply###
for zone in testzones['zoneid']:
	z1msw=Fetch(testzones, 'zoneid', zone, 'msw_sum')
	print(z1msw)
	temp=0
	for f in ftype:
		temp+= build[zone][f]['q']
		
	cons+=[temp<=z1msw]
	
###facility size###
for zone in testzones['zoneid']:
	for f in ftype:
		if f == 'IndF':
			cons+=[build[zone][f]['q']<=industrialmax]
			
		elif f == 'OnfarmF':
			cons+=[build[zone][f]['q']<=onfarmmax]
			
		elif f == 'CommF':
			cons+=[build[zone][f]['q']<=communitymax]


###define the problem###

prob = cp.Problem(cp.Minimize(obj), cons)

val = prob.solve(verbose = True)


###printing the build size###



