$title Alternative Futures: New Compost Infrastructure Across CA (ALTFUTURES,SEQ=1)

$onText
Spatial optimization

$offText

*figure out how to do inputs*
Set
*o  'available organic feedstocks'   / 23, 75, 64, 32 /
*total organic feedstocks minus existing processing capacity
* e 'existing composters'  / 44, 54, 82, 39 /
*'end markets'  / 32, 45, 21, 76 /
*'zones'    / 1, 2, 3, 4  /
*'composter types'      / 'industrial', 'on-farm', 'community' /;
  
q   'zones'   / nw 'northwest', sw 'southwest', se 'southeast', ne 'northeast'/
t   'typology'/ if 'industrial', of 'on-farm', cc 'community'/
j    'unit';

alias(q,qp);

$ontext
nw_industrial
nw_onfarm
se_industrial
...
$offText
Alias (q,qp);

Table node(q,*) 'zone data'

  zone       available     land     ej    y       
*               tons         tons    score score
   nw           3000         2000   69    1
   sw           4000         200    25    0 
   se           100          3000   88    1  
   ne           1000         1000   14    0
;

$onText
for now we are simplifying the model to not have distance nodes between zones and o, e, l
we will assume that everything that is produced in zone, stays in the zone to apply to in-zone land areas
$offText
   
Parameter
*for us this would be the distance matrices between potential sites
   dist(o,z) 'coordinates of existing facilities'
   w(m,n)      'weights associated with new-old facility pairs'
   v(n,n)      'weights associated with new-new facility pairs';

Parameter dist(n,n) 'distance between nodes (m)';

dist(a(n,np)) = sqrt(sqr(node(n,"x") - node(np,"x")) + sqr(node(n,"y") - node(np,"y")));
display dist;   

Scalar
*this will emissions factor, cost, etc
   dpow  'power on diameter in pressure loss equation'  / 5.33    /
   qpow  'power on flow in pressure loss equation'      / 2.00    /
   dmin  'minimum diameter of pipe'                     / 0.15    /
   dmax  'maximum diameter of pipe'                     / 2.00    /
   hloss 'constant in the pressure loss equation'       / 1.03e-3 /
   dprc  'scale factor in the investment cost equation' / 6.90e-2 /
   cpow  'power on diameter in the cost equation'       / 1.29    /
   r     'interest rate'                                / 0.10    /
   davg  'average diameter (geometric mean)'
   rr    'ratio of demand to supply';
   
Variable
*what goes into the equation (collection cost, hauling cost)
   q(n,n)    'flow on each arc - signed   (m**3 per sec)'
   d(n,n)    'pipe diameter for each arc             (m)'
   h(n)      'pressure at each node                  (m)'
   s(n)      'supply at reservoir nodes   (m**3 per sec)'
   pcost     'annual recurrent pump costs      (mill rp)'
   dcost     'investment costs for pipes       (mill rp)'
   wcost     'annual recurrent water costs     (mill rp)'
   cost      'total discounted costs           (mill rp)';
   
b.lo(j) = 0; 'lower bound of capacity builds of unit j'
b.up(j) = BMAX(j); 
   
Equation
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

Model emissions / peq, deq, emissions_obj /;
Model costmin / peq, deq, obj /;


solve emissions using dnlp minimizing emissions;
solve costmin using dnlp minimizing cost;




