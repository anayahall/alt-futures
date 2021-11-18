$ontext

PURPOSE: Toy Model for "Alt Futures - Holistic Compost Siting"

AUTHOR: Sasha & Anaya

DATE : Sept. 29, 2021

$offtext

*option profile = 1;
*^not sure what this does

***********************
***** DEFINE SETS *****
***********************
Sets
    j                               Units,
    q                               Zones,
    t                               Typology
;

*Alias(q,qp)
Alias(j,jk)
*^^^Is this where this should go?


*******************************************
***** CREATE INPUT GDX FILES FROM CSV *****
*******************************************
* sets *
$CALL csv2gdx ../GAMS_toy_sets/UnitsTable.csv output=UnitsTable.gdx id=j index=1 useHeader=y colCount=3

*****still need to bring in:*****
*typology
*distance
*zones

* parameters >> our scalars*
$CALL csv2gdx ../GAMS_toy_sets/ScalarTable.csv index=1 useHeader=y colCount=3




*******************************************
***** INITIATE SETS FROM GDX ?? *****
*******************************************
$GDXIN UnitsTable.gdx
$load j
$GDXIN
display j;

$ontext

Parameters
    UNITSTABLE(j,)

*convenience parameter, call out from Unitstable --
*QQQQ: how to identify this as "UNITSTABLE"???????
    BMAX(j) = UNITSTABLE(j, “bmax”)

;
*******************************************
***** VARIABLES & EQUATIONS           *****
*******************************************

Variable
*what goes into the equation (collection cost, hauling cost)
   x(j)     'capacity to build for each unit    (tons)'

*some constraints on capacity build out
*b.lo(j) = 0; 'lower bound of capacity builds of unit j'
* ignoring ^ for now!
    b.up(j) = BMAX(j)
    
    coll_cost       'collection cost'
    haul_cost       'hauling cost'
*    construction ????
    spread_cost     'speading cost '
    cost            'total project cost'

    coll_emis       'collection emissions'
    haul_emis       'hauling emissions'
    proc_emis       'compost processing emissions'
    landfill_emis   'avoided landfill emissions'
    seq             'net carbon sequestration'
    
    totalbuild      'total project buildout'
* ^ maybe this should be set above?
;
   
Equation
    cost_obj    'cost objective function'
    c_cost
    h_cost


    emissions_obj   'emissios:objective function'

    supply      'supply constraint'
    balance     'balance intake and output at each facility -- NOT AN EQAUALITY' 
;    

cost_obj..  cost =e= coll_cost + haul_cost + spread_cost

c_cost..    coll_cost =e= sum(j, x(j)*distance(j,jk)*a)
**NEED TO CROSSWALK Js to Qs-- THOUGH UNITSTABLE?



$ontext
*from example gams file:
   cont(n)   'flow conservation equation at each node'
   loss(n,n) 'pressure loss on each arc'
   peq       'pump cost equation'
   deq       'investment cost equation'
   weq       'water cost equation'
   obj       'objective function';

cont(n)..       sum(a(np,n), q(a)) - sum(a(n,np), q(a)) + s(n)$rn(n) =e= node(n,"demand");

loss(a(n,np)).. h(n) - h(np) =e= (hloss*dist(a)*abs(q(a))**(qpow-1)*q(a)/d(a)**dpow)$(qpow <> 2)
                              +   (hloss*dist(a)*abs(q(a))         *q(a)/d(a)**dpow)$(qpow  = 2);

peq..  pcost =e= sum(rn, s(rn)*node(rn,"pcost")*(h(rn) - node(rn,"height")));

deq..  dcost =e= dprc*sum(a, dist(a)*d(a)**cpow);

weq..  wcost =e= sum(rn, s(rn)*node(rn,"wcost"));

obj..  cost  =e= (pcost + wcost)/r + dcost;

d.lo(a)  = dmin;
d.up(a)  = dmax;
h.lo(rn) = node(rn,"height");
h.lo(dn) = node(dn,"height") + 7.5 + 5.0*node(dn,"demand");
s.lo(rn) = 0;
s.up(rn) = node(rn,"supply");
d.l(a)   = davg;
h.l(n)   = h.lo(n) + 1.0;
s.l(rn)  = node(rn,"supply")*rr;



*******************************************
***** DEFINE MODELS                   *****
*******************************************

Model emissions / supply, balance, emissions_obj /;
Model costmin / supply, balance, cost_obj /;


*******************************************
***** SOLVE MODELS                    *****
*******************************************


solve emissions using dnlp minimizing emissions;
solve costmin using dnlp minimizing cost;


*******************************************
***** SAVE OUTPUT SOMEHOW!            *****
*******************************************

$offtext