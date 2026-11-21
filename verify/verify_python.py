"""Independent cross-check of the MATLAB suite in ../matlab.

This script re-implements the same model in Python/SciPy and reproduces every
number and figure reported in the paper.  It exists so that the MATLAB results
can be checked against a second, independently written solver stack.

One deliberate exception: the QAOA angles below are NOT re-optimised here.  They
are the values returned by qh2dc_qaoa.m (fminsearch, five restarts, seed 7), and
they are pinned so that the figure and the statistics in this script are
identical to the MATLAB reference run.  The optimisation itself lives in
qh2dc_qaoa.m; this file only replays it.
"""
import numpy as np, pandas as pd, scipy.sparse as sp, json, os
from scipy.optimize import milp, LinearConstraint, Bounds, linprog, minimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

import os
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG=BASE+'/figures'; DAT=BASE+'/data'
plt.rcParams.update({'font.family':'serif','font.serif':['DejaVu Serif'],'font.size':8,
                     'axes.linewidth':0.7,'axes.grid':True,'grid.alpha':0.25,
                     'grid.linewidth':0.4,'legend.frameon':False,'savefig.dpi':300,
                     'axes.labelsize':8,'xtick.labelsize':7.5,'ytick.labelsize':7.5,'legend.fontsize':7})
C = dict(grid='#4a4a4a', ren='#2c7fb8', solar='#e08214', wind='#4d9221',
         h2='#8073ac', fc='#c51b7d', cap='#d7191c', load='#1a1a1a')

d=pd.read_csv(DAT+'/research_benchmark_168h.csv'); T=len(d)
FIX=d.fixed_ai_load_MW.values; FLX=d.baseline_flexible_load_MW.values
SOL=d.solar_MW.values; WND=d.wind_MW.values; REN=d.renewable_MW.values
CI=d.grid_carbon_kgCO2_per_MWh.values
CAP_NF=d.nonfirm_connection_cap_MW.values; CAP_PH=d.phased_connection_cap_MW.values
ELM,ETA_EL,FCM,ETA_FC,HMAX,H0=4.0,0.72,2.0,0.55,20.0,5.0
W_CO2,W_CURT,W_CYC,W_DEL=1.0,1.0,0.02,5.0
OFF=(0,3,7)
jt=np.where(FLX>0)[0]; E=FLX[jt]; J=len(jt)
CANDS=[[min(T-1,t0+o) for o in OFF] for t0 in jt]

# ---------------- flexible job table -----------------
jobs=pd.DataFrame({'job_id':np.arange(1,J+1),'day':d.day.values[jt],
    'baseline_hour':jt,'energy_MWh':E,
    'cand_1':[c[0] for c in CANDS],'cand_2':[c[1] for c in CANDS],'cand_3':[c[2] for c in CANDS],
    'release_h':jt,'deadline_h':[c[2] for c in CANDS]})
jobs.to_csv(DAT+'/research_flexible_jobs.csv',index=False)

# ---------------- scheduler -----------------
def solve(cap_vec, use_h2=True, flexible=False, fixed_place=None):
    K=[len(c) for c in CANDS]; nb=sum(K); off=np.cumsum([0]+K); N=5*T+nb
    def I(k): return slice(k*T,(k+1)*T)
    r_,c_,v_=[],[],[]
    for t in range(T):
        for (k,v) in [(0,1.),(1,-1.),(3,-1.),(2,1.)]: r_.append(t);c_.append(k*T+t);v_.append(v)
    for j in range(J):
        for kk,t in enumerate(CANDS[j]): r_.append(t);c_.append(5*T+off[j]+kk);v_.append(-E[j])
    A1=sp.coo_matrix((v_,(r_,c_)),shape=(T,N)); b1=FIX-REN
    r_,c_,v_=[],[],[]
    for t in range(T):
        r_.append(t);c_.append(4*T+t);v_.append(1.)
        if t>0: r_.append(t);c_.append(4*T+t-1);v_.append(-1.)
        r_.append(t);c_.append(1*T+t);v_.append(-ETA_EL)
        r_.append(t);c_.append(2*T+t);v_.append(1./ETA_FC)
    A2=sp.coo_matrix((v_,(r_,c_)),shape=(T,N)); b2=np.zeros(T); b2[0]=H0 if use_h2 else 0.
    r_,c_,v_=[],[],[]
    for j in range(J):
        for kk in range(K[j]): r_.append(j);c_.append(5*T+off[j]+kk);v_.append(1.)
    A3=sp.coo_matrix((v_,(r_,c_)),shape=(J,N)); b3=np.ones(J)
    r_,c_,v_=[],[],[]
    for t in range(T):
        r_.append(t);c_.append(1*T+t);v_.append(1.); r_.append(t);c_.append(3*T+t);v_.append(1.)
    A4=sp.coo_matrix((v_,(r_,c_)),shape=(T,N))
    lb=np.zeros(N); ub=np.full(N,np.inf)
    ub[I(0)]=cap_vec; ub[I(1)]=ELM if use_h2 else 0.; ub[I(2)]=FCM if use_h2 else 0.
    ub[I(3)]=REN; ub[I(4)]=HMAX if use_h2 else 0.
    lb[4*T+T-1]=H0 if use_h2 else 0.; ub[4*T+T-1]=H0 if use_h2 else 0.
    ub[5*T:]=1.
    if not flexible:
        for j in range(J):
            lb[5*T+off[j]]=1.; ub[5*T+off[j]]=1.
            for kk in range(1,K[j]): ub[5*T+off[j]+kk]=0.
    c=np.zeros(N); c[I(0)]=W_CO2*CI/1000.; c[I(3)]=W_CURT; c[I(1)]=W_CYC; c[I(2)]=W_CYC
    for j in range(J):
        for kk,t in enumerate(CANDS[j]): c[5*T+off[j]+kk]=W_DEL*(t-jt[j])
    cons=[LinearConstraint(A1,b1,b1),LinearConstraint(A2,b2,b2),
          LinearConstraint(A3,b3,b3),LinearConstraint(A4,-np.inf,REN)]
    integ=np.zeros(N); integ[5*T:]=1
    r=milp(c=c,constraints=cons,bounds=Bounds(lb,ub),integrality=integ,
           options={'time_limit':300,'mip_rel_gap':0.0})
    if r.status!=0: return None
    x=r.x; delays=np.array([CANDS[j][int(np.argmax(x[5*T+off[j]:5*T+off[j]+K[j]]))]-jt[j] for j in range(J)])
    pg,pe,pf,pc,h=x[0:T],x[T:2*T],x[2*T:3*T],x[3*T:4*T],x[4*T:5*T]
    sched=np.zeros(T)
    for j in range(J): sched[jt[j]+delays[j]]+=E[j]
    return dict(pg=pg,pe=pe,pf=pf,pc=pc,h=h,delays=delays,sched=sched,
                grid=pg.sum(),peak=pg.max(),co2=(pg*CI).sum()/1000.,curt=pc.sum(),
                util=100*(1-pc.sum()/REN.sum()),EL=pe.sum(),FC=pf.sum(),
                avgdelay=delays.mean(),maxdelay=delays.max(),shifted=100*np.mean(delays>0),
                viol=np.maximum(0,pg-cap_vec).sum())

def min_cap(use_h2,flexible,lo=0.,hi=16.,it=24):
    for _ in range(it):
        mid=(lo+hi)/2
        if solve(np.full(T,mid),use_h2,flexible) is not None: hi=mid
        else: lo=mid
    return hi

res={}
L0=FIX+FLX
res['R0']=dict(grid=L0.sum(),peak=L0.max(),co2=(L0*CI).sum()/1000.,util=0.,
               avgdelay=0.,shifted=0.,EL=0.,FC=0.,curt=0.,viol=0.)
res['R1']=solve(np.full(T,np.inf),False,False)
c2=min_cap(True,False); c3=min_cap(True,True)
# R2 must be evaluated AT the capacity it reports.  Solving with cap=inf and
# then quoting c2 alongside describes an operating point that was never solved
# (its true peak import is 12.59 MW, not 10.59 MW).
res['R2']=solve(np.full(T,c2),True,False); res['R2']['mincap']=c2
# Fig. 5 counterfactual: unconstrained H2-only dispatch, replayed against the
# non-firm envelope.  Not a minimisation of that violation.
res['R2u']=solve(np.full(T,np.inf),True,False)
res['R3']=solve(np.full(T,c3),True,True); res['R3']['mincap']=c3
res['R4']=solve(CAP_NF,True,True); res['R5']=solve(CAP_PH,True,True)
res['R4']['viol']=np.maximum(0,res['R4']['pg']-CAP_NF).sum()
res['R5']['viol']=np.maximum(0,res['R5']['pg']-CAP_PH).sum()
C0=res['R0']['peak']
rep=[('R0','Grid-only reference',res['R0']['peak']),('R1','Renewable supply',res['R1']['peak']),
     ('R2','Green-H$_2$ assisted',c2),('R3','H$_2$ + workload flexibility',c3),
     ('R4','Non-firm envelope',res['R4']['peak']),('R5','Phased envelope',res['R5']['peak'])]
rows=[]
for k,nm,cap in rep:
    r=res[k]
    rows.append(dict(scenario=k,label=nm,grid_MWh=r['grid'],conn_MW=cap,
        red_pct=100*(1-cap/C0),co2_t=r['co2'],ren_util=r['util'],
        avg_delay=r['avgdelay'],shifted=r['shifted'],viol=r.get('viol',0.)))
out=pd.DataFrame(rows); out.to_csv(DAT+'/research_results_verified.csv',index=False)
print(out.to_string(index=False))

# ================= QUBO / QAOA =================
A_PEN,W_STR,W_C,W_R,W_D,W_X=40.0,6.0,1.0,1.5,0.30,2.5
def build_qubo(day=0):
    jj=[t for t in range(24*day,24*(day+1)) if FLX[t]>0]
    Ej=[FLX[t] for t in jj]; Jd=len(jj); K=3
    cd=[[min(T-1,t0+o) for o in OFF] for t0 in jj]
    n=Jd*K; Q=np.zeros((n,n)); const=0.
    vi=lambda j,k: j*K+k
    for j in range(Jd):
        for k in range(K):
            t=cd[j][k]; head=CAP_NF[t]-(FIX[t]-REN[t])
            Q[vi(j,k),vi(j,k)] += (W_STR*max(0.,Ej[j]-head) + W_C*CI[t]*Ej[j]/1000.
                                   - W_R*min(Ej[j],max(0.,REN[t]-FIX[t])) + W_D*(cd[j][k]-jj[j]))
    for j in range(Jd):
        for k in range(K):
            Q[vi(j,k),vi(j,k)] -= A_PEN
            for l in range(k+1,K): Q[vi(j,k),vi(j,l)] += 2*A_PEN
        const += A_PEN
    for j in range(Jd):
        for j2 in range(j+1,Jd):
            for k in range(K):
                for l in range(K):
                    if cd[j][k]==cd[j2][l]: Q[vi(j,k),vi(j2,l)] += W_X*Ej[j]*Ej[j2]/10.
    return Q,const,n,Jd,K,jj,cd

Q,QC,nq,Jd,Kd,jj,cd=build_qubo(0)
bits=((np.arange(2**nq)[:,None]>>np.arange(nq))&1).astype(float)
Ecost=np.einsum('si,ij,sj->s',bits,np.triu(Q),bits)+QC
onehot=np.all(bits.reshape(-1,Jd,Kd).sum(axis=2)==1,axis=1)
feas=np.where(onehot)[0]; best=feas[np.argmin(Ecost[feas])]

def qaoa_state(par,p,Es):
    psi=np.ones(2**nq)/np.sqrt(2**nq); g=par[:p]; b=par[p:]
    for i in range(p):
        psi=psi*np.exp(-1j*g[i]*Es); c_,s_=np.cos(b[i]),-1j*np.sin(b[i])
        psi=psi.reshape([2]*nq)
        for q in range(nq):
            psi=np.moveaxis(psi,q,0); a0,a1=psi[0].copy(),psi[1].copy()
            psi[0]=c_*a0+s_*a1; psi[1]=s_*a0+c_*a1; psi=np.moveaxis(psi,0,q)
        psi=psi.reshape(-1)
    return psi
Es=Ecost/np.max(np.abs(Ecost))
def fobj(par,p): pr=np.abs(qaoa_state(par,p,Es))**2; return float(pr@Ecost)
# Reference angles: the optimised values returned by the MATLAB/Octave
# implementation (fminsearch, 5 restarts, seed 7).  Fixing them here makes the
# figure and the reported statistics identical to the MATLAB reference run.
REF={1:np.array([8.7833172550,-0.3786942217]),
     2:np.array([7.9399897710,23.0519631284,2.7535202027,2.9468156799])}
qaoa_res={}
for p in [1,2]:
    class _B: pass
    bb=_B(); bb.x=REF[p]; bb.fun=fobj(REF[p],p)
    pr=np.abs(qaoa_state(bb.x,p,Es))**2
    tf=feas[np.argmax(pr[feas])]
    qaoa_res[p]=dict(exp=bb.fun,par=list(np.asarray(bb.x)),feas_mass=100*pr[feas].sum(),
        p_opt=100*pr[best],match=bool(tf==best),gap=float(abs(Ecost[tf]-Ecost[best])),pr=pr)
    print(f"p={p} <C>={bb.fun:.3f} feas={qaoa_res[p]['feas_mass']:.2f}% P(opt)={qaoa_res[p]['p_opt']:.3f}% match={qaoa_res[p]['match']}")
print("classical best feasible energy %.4f"%Ecost[best],"nfeas",len(feas),"states",2**nq)
sel=[cd[j][int(np.argmax(bits[best].reshape(Jd,Kd)[j]))] for j in range(Jd)]
print("QAOA/exact assignment hours",sel,"baseline",jj)

# ================= FIGURES =================
hrs=np.arange(T)
# ---- gr1 architecture ----
fig,ax=plt.subplots(figsize=(6.5,3.05)); ax.set_xlim(0,10); ax.set_ylim(0,4.6); ax.axis('off'); ax.grid(False)
def box(x,y,w,h,txt,fc,ec,fs=7.0):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.045,rounding_size=0.09",
        fc=fc,ec=ec,lw=0.8)); ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=fs)
def arr(x1,y1,x2,y2,st='-|>',ls='-'):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle=st,mutation_scale=8,lw=0.7,color='#555',linestyle=ls))
box(0.15,3.35,2.5,0.95,"GPU cluster trace\n(job class, priority,\nutilisation)",'#eef4fa','#2c7fb8')
box(0.15,2.05,2.5,0.95,"Renewable and\ncarbon-intensity\ntime series",'#eef4fa','#2c7fb8')
box(0.15,0.75,2.5,0.95,"Connection envelope\n(firm / phased /\nnon-firm)",'#eef4fa','#2c7fb8')
box(3.15,1.85,2.15,2.45,"Data-engineering\nlayer\n\n• validate, clean\n• classify fixed vs.\n  delay-tolerant\n• map to power\n• hourly join",'#f7f2fb','#8073ac')
box(3.15,0.35,2.15,1.05,"Analytical\nbenchmark table",'#fdf3e6','#e08214')
box(5.85,2.95,1.95,1.35,"QUBO builder\n+ QAOA\nplacement",'#fdeef0','#c51b7d')
box(5.85,1.35,1.95,1.35,"Classical dispatch\n(grid, H$_2$, fuel cell)",'#eefaf0','#4d9221')
box(8.25,1.85,1.6,1.95,"Connection\nfeasibility\nand\nSLA metrics",'#f2f2f2','#4a4a4a')
for y in (3.82,2.52,1.22): arr(2.68,y,3.12,y if y<3 else 3.4)
arr(4.22,1.82,4.22,1.45); arr(5.33,3.6,5.82,3.6); arr(5.33,2.3,5.82,2.0)
arr(6.82,2.92,6.82,2.73); arr(7.83,3.6,8.3,3.3); arr(7.83,2.0,8.3,2.3)
ax.add_patch(FancyArrowPatch((9.05,1.82),(9.05,0.55),arrowstyle='-|>',mutation_scale=8,lw=0.7,color='#555',linestyle=(0,(3,2))))
ax.add_patch(FancyArrowPatch((9.05,0.55),(6.82,0.55),arrowstyle='-',mutation_scale=8,lw=0.7,color='#555',linestyle=(0,(3,2))))
ax.add_patch(FancyArrowPatch((6.82,0.55),(6.82,1.32),arrowstyle='-|>',mutation_scale=8,lw=0.7,color='#555',linestyle=(0,(3,2))))
ax.text(7.9,0.35,"infeasible: re-dispatch / re-place",fontsize=6.3,color='#555',ha='center')
fig.tight_layout(pad=0.15); fig.savefig(FIG+'/gr1.pdf'); fig.savefig(FIG+'/gr1.png'); plt.close(fig)

# ---- gr2 benchmark week ----
fig,axs=plt.subplots(3,1,figsize=(6.5,4.25),sharex=True,
                     gridspec_kw={'height_ratios':[1.25,1,0.9],'hspace':0.16})
a=axs[0]
a.plot(hrs,FIX,color=C['load'],lw=0.9,label='Fixed AI demand')
a.bar(hrs,FLX,color='#b0b0b0',width=0.85,label='Baseline flexible bundles')
a.plot(hrs,REN,color=C['ren'],lw=0.9,label='Renewable supply')
a.set_ylabel('Power (MW)'); a.legend(ncol=3,loc='upper left',bbox_to_anchor=(0,1.28))
a.set_ylim(0,17)
a=axs[1]
a.fill_between(hrs,0,SOL,color=C['solar'],alpha=0.55,lw=0,label='Solar')
a.fill_between(hrs,SOL,SOL+WND,color=C['wind'],alpha=0.55,lw=0,label='Wind')
a.set_ylabel('Power (MW)'); a.legend(ncol=2,loc='upper right')
a=axs[2]
a.step(hrs,CAP_NF,where='mid',color=C['cap'],lw=0.9,label='Non-firm envelope')
a.step(hrs,CAP_PH,where='mid',color='#377eb8',lw=0.9,ls='--',label='Phased envelope')
a2=a.twinx(); a2.plot(hrs,CI,color='#777',lw=0.6,alpha=0.8); a2.set_ylabel('Carbon int.\n(kg/MWh)',color='#777')
a2.tick_params(colors='#777',labelsize=7); a2.grid(False)
a.set_ylabel('Cap (MW)'); a.set_xlabel('Hour of the 168 h benchmark'); a.legend(ncol=2,loc='lower right')
a.set_xlim(0,167); a.set_xticks(np.arange(0,169,24))
fig.tight_layout(pad=0.2); fig.savefig(FIG+'/gr2.pdf'); fig.savefig(FIG+'/gr2.png'); plt.close(fig)

# ---- gr4 capacity ladder ----
fig,ax=plt.subplots(figsize=(6.5,2.75))
labs=['R0\nGrid only','R1\n+ Renewables','R2\n+ Green H$_2$','R3\n+ Workload\nflexibility','R4\nNon-firm\nenvelope','R5\nPhased\nenvelope']
vals=[r[2] for r in rep]; cols=['#8c8c8c','#2c7fb8','#8073ac','#4d9221','#c51b7d','#e08214']
b=ax.bar(range(6),vals,color=cols,width=0.62,edgecolor='k',linewidth=0.4)
for i,(bb_,v) in enumerate(zip(b,vals)):
    red=100*(1-v/C0)
    ax.text(bb_.get_x()+bb_.get_width()/2,v+0.25,f"{v:.2f} MW",ha='center',fontsize=7)
    if i>0: ax.text(bb_.get_x()+bb_.get_width()/2,v/2,f"-{red:.1f}%",ha='center',fontsize=7,color='w',fontweight='bold')
ax.axhline(C0,color='#8c8c8c',ls=':',lw=0.8)
ax.set_xticks(range(6)); ax.set_xticklabels(labs); ax.set_ylabel('Required connection\ncapacity (MW)')
ax.set_ylim(0,17.5); ax.tick_params(axis='x',pad=2)
fig.subplots_adjust(left=0.105,right=0.99,top=0.97,bottom=0.235)
fig.savefig(FIG+'/gr4.pdf'); fig.savefig(FIG+'/gr4.png'); plt.close(fig)

# ---- gr5 non-firm 48 h ----
r4=res['R4']; H=48; h4=np.arange(H)
base=res['R2u']   # unconstrained H2-only dispatch, replayed against the envelope
fig,axs=plt.subplots(3,1,figsize=(6.5,4.5),sharex=True,
                     gridspec_kw={'height_ratios':[1.15,1.15,0.75],'hspace':0.15})
a=axs[0]
a.bar(h4,base['pg'][:H],width=0.8,color='#c9c9c9',edgecolor='#9a9a9a',lw=0.3,label='Import without workload flexibility')
a.step(h4,CAP_NF[:H],where='mid',color=C['cap'],lw=1.1,label='Non-firm envelope $C_t$')
ex=np.maximum(0,base['pg'][:H]-CAP_NF[:H])
a.bar(h4,ex,bottom=CAP_NF[:H],width=0.8,color=C['cap'],alpha=0.55,lw=0,label='Envelope exceedance')
a.set_ylabel('Grid import (MW)'); a.set_ylim(0,13.5)
a.legend(ncol=3,loc='upper left',bbox_to_anchor=(-0.02,1.42),columnspacing=1.0)
a=axs[1]
a.bar(h4,r4['pg'][:H],width=0.8,color=C['grid'],label='Optimised grid import')
a.step(h4,CAP_NF[:H],where='mid',color=C['cap'],lw=1.1,label='Non-firm envelope $C_t$')
a.set_ylabel('Grid import (MW)'); a.set_ylim(0,13.5)
a.legend(ncol=2,loc='upper left',columnspacing=1.0)
a.text(0.985,0.88,'zero exceedance, zero unserved energy',transform=a.transAxes,ha='right',fontsize=6.8,color=C['wind'])
a=axs[2]
a.bar(h4,FLX[:H],width=0.8,color='#c9c9c9',edgecolor='#9a9a9a',lw=0.3,label='Baseline slot')
a.bar(h4,r4['sched'][:H],width=0.42,color=C['wind'],label='Selected slot')
for s0,s1 in [(7.5,14.5),(31.5,38.5)]: a.axvspan(s0,s1,color=C['cap'],alpha=0.07,lw=0)
a.text(11,11.9,'constrained window',ha='center',fontsize=6.4,color=C['cap'])
a.text(35,11.9,'constrained window',ha='center',fontsize=6.4,color=C['cap'])
a.set_ylabel('Flexible\nbundle (MW)'); a.set_xlabel('Hour of the 168 h benchmark (first 48 h shown)')
a.legend(ncol=2,loc='upper center',bbox_to_anchor=(0.5,0.80),columnspacing=1.0,fontsize=6.6); a.set_ylim(0,15)
a.set_xlim(-0.6,H-0.4); a.set_xticks(np.arange(0,H+1,6))
fig.tight_layout(pad=0.2); fig.savefig(FIG+'/gr5.pdf'); fig.savefig(FIG+'/gr5.png'); plt.close(fig)

# ---- gr6 hydrogen ----
fig,axs=plt.subplots(2,1,figsize=(6.5,3.2),sharex=True,gridspec_kw={'height_ratios':[1,1],'hspace':0.13})
a=axs[0]
a.bar(hrs,res['R1']['pc'],width=1.0,color='#d9d9d9',label='Renewable surplus without H$_2$')
a.bar(hrs,res['R2']['pe'],width=0.55,color=C['h2'],label='Electrolyser intake')
a.bar(hrs,-res['R2']['pf'],width=0.55,color=C['fc'],label='Fuel-cell output')
a.axhline(0,color='k',lw=0.5); a.set_ylabel('Power (MW)')
a.legend(ncol=3,loc='upper left',bbox_to_anchor=(-0.02,1.40),columnspacing=1.0)
a=axs[1]
a.plot(hrs,res['R2']['h'],color=C['h2'],lw=1.0,label='H$_2$ inventory')
a.axhline(H0,color='#888',ls=':',lw=0.7); a.axhline(HMAX,color=C['cap'],ls='--',lw=0.7,label='Storage limit')
a.set_ylabel('H$_2$ stored\n(MWh$_{\\mathrm{H2}}$)'); a.set_xlabel('Hour of the 168 h benchmark'); a.legend(ncol=2,loc='upper right')
a.set_xlim(0,167); a.set_xticks(np.arange(0,169,24)); a.set_ylim(0,23.5)
fig.subplots_adjust(left=0.095,right=0.99,top=0.865,bottom=0.145,hspace=0.14)
fig.savefig(FIG+'/gr6.pdf'); fig.savefig(FIG+'/gr6.png'); plt.close(fig)

# ---- gr3 QAOA ----
# The cost operator is a rescaled real diagonal, so the expected cost is NOT
# pi-periodic in gamma.  The landscape is therefore drawn over the range that
# actually contains the optimised angles rather than a folded [0,pi] square.
ng=61
gs=np.linspace(0,12.0,ng); bs=np.linspace(-1.5,1.5,ng); land=np.zeros((ng,ng))
for i,g in enumerate(gs):
    for j2,b_ in enumerate(bs): land[j2,i]=fobj(np.array([g,b_]),1)
fig=plt.figure(figsize=(6.5,2.6))
gsx=fig.add_gridspec(1,2,width_ratios=[1,1.3],wspace=0.52,left=0.075,right=0.985,top=0.90,bottom=0.19)
a=fig.add_subplot(gsx[0])
im=a.contourf(gs,bs,land,levels=22,cmap='viridis'); a.grid(False)
pp=qaoa_res[1]['par']; a.plot(pp[0],pp[1],'*',color='w',ms=9,mec='k',mew=0.6)
a.annotate('optimised angles',xy=(pp[0],pp[1]),xytext=(2.1,-1.15),fontsize=6.4,color='w',
           arrowprops=dict(arrowstyle='->',lw=0.6,color='w'))
a.set_xlabel(r'$\gamma$'); a.set_ylabel(r'$\beta$')
a.set_title('(a) $p=1$ energy landscape',fontsize=7.5,pad=3)
cb=fig.colorbar(im,ax=a,pad=0.03,fraction=0.05)
cb.set_label('Expected QUBO cost',fontsize=6.5,labelpad=1); cb.ax.tick_params(labelsize=6.0,pad=1)
a=fig.add_subplot(gsx[1])
pr=qaoa_res[1]['pr']; order=np.argsort(Ecost); ffl=onehot[order]
a.scatter(np.arange(2**nq)[~ffl],pr[order][~ffl]*100,s=1.4,color='#d0d0d0',label='Infeasible states (4015)')
a.scatter(np.arange(2**nq)[ffl],pr[order][ffl]*100,s=6,color=C['fc'],label='Feasible one-hot states (81)')
kbest=int(np.where(order==best)[0][0])
a.annotate('exact best feasible\nassignment',xy=(kbest,pr[best]*100),xytext=(620,0.012),
           fontsize=6.4,arrowprops=dict(arrowstyle='->',lw=0.6,color='k'))
a.set_yscale('log'); a.set_xlabel('Basis states ordered by QUBO cost')
a.set_ylabel('Measurement probability (%)')
a.set_title('(b) output distribution at the optimised angles',fontsize=7.5,pad=3)
a.legend(loc='lower left',fontsize=6.4); a.set_xlim(-50,4146); a.set_ylim(1e-7,2)
fig.savefig(FIG+'/gr3.pdf'); fig.savefig(FIG+'/gr3.png'); plt.close(fig)

json.dump({'qaoa':{str(k):{kk:vv for kk,vv in v.items() if kk!='pr'} for k,v in qaoa_res.items()},
           'best_energy':float(Ecost[best]),'n_feasible':int(len(feas)),'n_states':int(2**nq),
           'assignment_hours':[int(s) for s in sel],'baseline_hours':[int(s) for s in jj],
           'R1_curt':float(res['R1']['curt']),'R2_EL':float(res['R2']['EL']),'R2_FC':float(res['R2']['FC']),
           'R3_maxdelay':int(res['R3']['maxdelay']),'R4_maxdelay':int(res['R4']['maxdelay']),
           'R5_maxdelay':int(res['R5']['maxdelay'])},open(DAT+'/verification_summary.json','w'),indent=1)
print("figures + summary written")
