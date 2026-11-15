import math
c=299792458.0
# R1
f0=10.5e9; vp=25; vs=35
bp=vp/c; bs=vs/c
brel=(bp+bs)/(1+bp*bs)
fr=f0*(1+brel)/(1-brel); print("R1 exact",fr-f0)
cb=3e8; f1=f0*(cb+vs)/(cb-vp); f2=f1*(cb+vp)/(cb-vs); print("R1 classical",f2-f0, 2*(vp+vs)*f0/cb)
# R2
v=336; f=480; e=0.6*0.02; lam=v/f
L=[(2*n-1)*lam/4-e for n in range(1,10)]; L=[x for x in L if x<=1.0]; print("R2",L,[L[i+1]-L[i] for i in range(len(L)-1)],len(L))
# R3
v=340; w=10; vo=5; f0=500
print("R3 speed seen",v+w+vo,"freq",f0*(v+w+vo)/(v+w),"lam",(v+w)/f0)
# R4
import numpy as np
T=np.linspace(400,484,100001); fw=(1/(2*0.5))*np.sqrt(T/0.01); b=abs(fw-210)
print("R4 max",b.max(),"min",b.min(),"at484",abs(10*math.sqrt(484)-210))
