import numpy as np
v=340.0
# R1: car toward wall, observer behind
f0=500.0
us=np.linspace(1e-3,v-1e-3,200001)
f1=f0*v/(v+us); f2=f0*v/(v-us); fd=f0*(v+us)/(v-us)
A=np.all((f2>f0)&(f0>f1)); B=np.allclose(2*f1*f2/(f1+f2),f0); C=np.all(fd>f2)
D=f2-f1>50
print("R1",A,B,C,"D all",D.all(),"D any",D.any(),"threshold u",us[np.argmax(D)])
# R2: open pipe 60cm, closed pipe L in (15,30) cm
v2=330.0
Ls=np.linspace(0.15+1e-6,0.30-1e-6,200001)
n1=v2/(2*0.60); n2=2*v2/(2*0.60); n3=v2/(4*Ls)
print("R2 n2>n3>n1 all:",np.all((n2>n3)&(n3>n1)), "n1,n2,n3 range",n1,n2,n3.min(),n3.max())
# R3: oblique Doppler, sweep u and simulate reception by brute force
d=170.0; f0=680.0
for u in [1,20,100,200,300,339]:
    te=np.linspace(-20,20,4000001)  # emission times, source x=u*te, N at te=0
    x=u*te; r=np.hypot(x,d); tr=te+r/v
    cos=-x/r  # cos angle between velocity (+x) and source->observer vector (-x,d)
    f=f0*v/(v-u*cos)
    # frequency also from numeric dte/dtr
    fnum=f0*np.gradient(te,tr)
    i=np.argmin(abs(f-f0))
    print("R3 u",u,"tr at f0:",tr[i],"numeric f at that point",fnum[i],"unique sign change",np.sum(np.diff(np.sign(f-f0))!=0))
