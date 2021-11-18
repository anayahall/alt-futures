$title test GAMS Run 1

$onText
First run attempt to make GAMS work.
Will be used as a baseline for developing the holistic siting model for
composters

Hall, Anaya
$offtext

Set
candidates 'candidate zones for new composters' / q*i /

$Table

Parameter

Variable


Positive Variable

Equation


$ej

Model
    c1 'problem without ej'
    c2 'problem with ej'
    
