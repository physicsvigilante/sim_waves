# independent numeric check: heard frequency via emission-time root + finite difference
import math
def brentq(g,a,b,xtol=1e-14):
    ga=g(a)
    for _ in range(200):
        m=(a+b)/2; gm=g(m)
        if (gm>0)==(ga>0): a,ga=m,gm
        else: b=m
    return (a+b)/2
def te(E,R,t,v=340.0,w=(0,0,0)):
    def g(tau):
        r=R(t); e=E(tau)
        d=[r[i]-e[i]-w[i]*(t-tau) for i in range(len(r))]
        return math.sqrt(sum(c*c for c in d))-v*(t-tau)
    lo=t-1.0
    while g(lo)>0: lo=t-(t-lo)*2
    return brentq(g,lo,t,xtol=1e-14)
def fh(E,R,t,f=500.0,h=1e-5,**kw):
    return f*(te(E,R,t+h,**kw)-te(E,R,t-h,**kw))/(2*h)
def lin(at,vel,starts=None):
    def p(t):
        if starts is None: return [a+u*t for a,u in zip(at,vel)]
        return list(at) if t<starts else [a+u*(t-starts) for a,u in zip(at,vel)]
    return p
def circ(at,c,speed,sense):
    R=math.hypot(at[0]-c[0],at[1]-c[1]); th=math.atan2(at[1]-c[1],at[0]-c[0]); om=sense*speed/R
    return lambda t:[c[0]+R*math.cos(th+om*t),c[1]+R*math.sin(th+om*t)]
def arr(E,R,tau,v=340.0,w=(0,0,0)):
    def g(t):
        return te(E,R,t,v,w)-tau
    hi=tau+1
    while g(hi)<0: hi=tau+(hi-tau)*2
    return brentq(g,tau,hi,xtol=1e-13)
if __name__=="__main__":
    st=lambda at: lin(at,[0]*len(at))
    # c1 perpendicular pass
    E=lin([-100,0],[20,0]); R=st([0,50])
    print("c1 f(t=5)",fh(E,R,5), "arr(5)",arr(E,R,5),"f at arr(5)",fh(E,R,arr(E,R,5)), "f(t=1)",fh(E,R,1),"f(t=12)",fh(E,R,12), "te(5)",te(E,R,5))
    # c2 wind at angle
    w=(6,8)
    print("c2 wind f(t=3)",fh(E,R,3,w=w),"arr(5)",arr(E,R,5,w=w),"f(emitted 5)",fh(E,R,arr(E,R,5,w=w),w=w))
    # c3 moving listener oblique
    R2=lin([0,50],[0,-12])
    print("c3", fh(E,R2,2), fh(E,R2,7), te(E,R2,7))
    # 3D
    E3=lin([-100,0,0],[20,0,5]); R3=lin([0,50,30],[3,-12,4])
    print("c4 3d", fh(E3,R3,2), fh(E3,R3,9), te(E3,R3,9), arr(E3,R3,1))
    w3=(5,-7,9)
    print("c5 3d wind", fh(E3,R3,2,w=w3), fh(E3,R3,9,w=w3))
    # circles
    Ec=circ([2,0],[0,0],30,1); Rs=st([10,0])
    print("d1 circ src", fh(Ec,Rs,0.3), fh(Ec,Rs,1.0), te(Ec,Rs,1.0), arr(Ec,Rs,0.2))
    Rc=circ([10,3],[10,0],20,-1)
    print("d2 both circ", fh(Ec,Rc,0.3), fh(Ec,Rc,1.0))
    Em=lin([-50,1],[25,0])
    print("d3 lin src circ lis", fh(Em,Rc,0.5), fh(Em,Rc,3.0))
    print("d4 circ wind", fh(Ec,Rs,0.3,w=(8,-5)), fh(Ec,Rc,1.0,w=(8,-5)))
    # starts
    Es=lin([0,0],[10,0],starts=5)
    print("e1 starts oblique", fh(Es,st([100,40]),5.2,v=350), fh(Es,st([100,40]),5.4,v=350), fh(Es,st([100,40]),9,v=350))
    Rst=lin([100,40],[-20,5],starts=2)
    print("e2 lis starts", fh(Es,Rst,1.0,v=350), fh(Es,Rst,3,v=350), fh(Es,Rst,8,v=350), te(Es,Rst,8,v=350))
    E=lin([-100,-10],[20,0]); R=st([0,30])
    print("g1 image", fh(E,R,2), fh(E,R,arr(E,R,5)))
    E=lin([-100,-40],[20,10]); R=st([0,30])
    print("k2 image ok", fh(E,R,2), "crossed", fh(E,R,8))
