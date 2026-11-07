"""Small finite multiclass family with disjoint-data calibration.

No model receives future labels, class-balancing weights, early-stop validation,
or a parameter search. A temperature map preserves argmax. Identity-shrunk
Dirichlet below is OUR bounded regularized variant, not Kull's ODIR penalty.
Calibration fitting and observed reliability do not certify market probabilities.
"""
import warnings
import numpy as np
from scipy.optimize import minimize,minimize_scalar
from scipy.special import logsumexp,softmax
from sklearn.exceptions import ConvergenceWarning
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

BASES=('ridge','tree')
MAPS=('raw','temperature','dirichlet_identity')
CANDIDATES=tuple(b+'_'+c for b in BASES for c in MAPS)+('frequency',)
EPSILON=1e-12


def probabilities(p):
    p=np.asarray(p,float)
    if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all() or (p<0).any() or (p>1).any() or not np.allclose(p.sum(axis=1),1,atol=1e-10,rtol=0):
        raise ValueError('finite canonical3class probability simplex required')
    q=np.maximum(p,EPSILON);return q/q.sum(axis=1,keepdims=True)


def labels(y):
    a=np.asarray(y)
    if a.ndim!=1 or a.dtype.kind not in 'iu' or not np.isin(a,[0,1,2]).all():raise ValueError('canonical integer target labels required')
    return a.astype(int)


def fit_bases(x,y):
    x=np.asarray(x,float);y=labels(y)
    if x.ndim!=2 or len(x)!=len(y) or len(y)<50 or not np.isfinite(x).all() or min(np.bincount(y,minlength=3))<5:
        raise ValueError('complete training matrix/minimum50events and5perclass required')
    mean=x.mean(axis=0);scale=x.std(axis=0);scale=np.where(scale>0,scale,1.)
    z=np.clip((x-mean)/scale,-5.,5.)
    models={}
    for name in BASES:
        estimator=(LogisticRegression(C=.1,solver='lbfgs',max_iter=2000,tol=1e-9,random_state=331)
                   if name=='ridge' else HistGradientBoostingClassifier(max_iter=32,max_leaf_nodes=3,
                       min_samples_leaf=20,learning_rate=.05,l2_regularization=10,
                       early_stopping=False,random_state=331))
        with warnings.catch_warnings():
            warnings.simplefilter('error',ConvergenceWarning);estimator.fit(z,y)
        if not np.array_equal(estimator.classes_,[0,1,2]):raise ValueError('training class identity drift')
        models[name]=estimator
    return dict(mean=mean,scale=scale,models=models,n=len(y),classes=np.bincount(y,minlength=3).tolist())


def predict_bases(bundle,x):
    x=np.asarray(x,float)
    if x.ndim!=2 or x.shape[1]!=len(bundle['mean']) or not np.isfinite(x).all():raise ValueError('complete exactfeature matrix required')
    if not len(x):return {k:np.empty((0,3)) for k in BASES}
    z=np.clip((x-bundle['mean'])/bundle['scale'],-5.,5.)
    return {name:probabilities(model.predict_proba(z)) for name,model in bundle['models'].items()}


def export_bases(bundle):
    """Transparent audit export; production predictions still use pinned sklearn.

    Numeric features only; tree leaf values already include learning rate.
    This intentionally fails rather than inventing support for categorical
    bitsets, another version's node schema or noncanonical target classes.
    """
    result=dict(mean=bundle['mean'].tolist(),scale=bundle['scale'].tolist(),models={})
    ridge=bundle['models']['ridge']
    result['models']['ridge']=dict(kind='multinomial_logit',coef=ridge.coef_.tolist(),intercept=ridge.intercept_.tolist())
    tree=bundle['models']['tree'];stages=[]
    for predictors in tree._predictors:
        if len(predictors)!=3:raise ValueError('threeclass tree stage required')
        stage=[]
        for predictor in predictors:
            if any(bool(n['is_categorical']) for n in predictor.nodes):raise ValueError('categorical tree audit unsupported')
            stage.append([dict(value=float(n['value']),feature=int(n['feature_idx']),threshold=float(n['num_threshold']),
                left=int(n['left']),right=int(n['right']),leaf=bool(n['is_leaf'])) for n in predictor.nodes])
        stages.append(stage)
    result['models']['tree']=dict(kind='histogram_boosted_numeric',baseline=tree._baseline_prediction.ravel().tolist(),stages=stages)
    return result


def objective(theta,logp,y):
    """Mean NLL plus identity/intercept L2; analytic gradient, fixedlambda=1.

    Twelve raw3class parameters:9W and3b. Sum-vs-mean androw orientation are
    explicit. Not paperODIR (which penalizes offdiagonals/intercepts only).
    """
    w=theta[:9].reshape(3,3);b=theta[9:];logits=logp@w.T+b
    q=softmax(logits,axis=1);n=len(y);r=q.copy();r[np.arange(n),y]-=1;r/=n
    dw=w-np.eye(3)
    loss=float(np.mean(logsumexp(logits,axis=1)-logits[np.arange(n),y])+
               .5*np.sum(dw*dw)/3+.5*np.sum(b*b)/3)
    gradient=np.r_[(r.T@logp+dw/3).ravel(),r.sum(axis=0)+b/3]
    return loss,gradient


def fit_maps(p,y):
    p=probabilities(p);y=labels(y)
    if len(p)!=len(y) or len(y)<30 or min(np.bincount(y,minlength=3))<3:
        return dict(state='UNAVAILABLE',reason='calibration_needs30and3perclass',raw=dict(kind='raw'),temperature=None,dirichlet_identity=None)
    z=np.log(p)
    def nll(logt):
        logits=z/np.exp(logt)
        return float(np.mean(logsumexp(logits,axis=1)-logits[np.arange(len(y)),y]))
    t=minimize_scalar(nll,bounds=(-np.log(10.),np.log(10.)),method='bounded',options={'xatol':1e-10,'maxiter':1000})
    initial=np.r_[np.eye(3).ravel(),np.zeros(3)]
    d=minimize(objective,initial,args=(z,y),method='L-BFGS-B',jac=True,bounds=[(-5.,5.)]*12,
               options={'maxiter':1000,'ftol':1e-12,'gtol':1e-8})
    return dict(state='FIT' if t.success and d.success else 'OPTIMIZER_FAILURE',n=len(y),classes=np.bincount(y,minlength=3).tolist(),
        raw=dict(kind='raw'),
        temperature=dict(kind='temperature',temperature=float(np.exp(t.x)),loss=float(t.fun)) if t.success else None,
        dirichlet_identity=dict(kind='dirichlet_identity',w=d.x[:9].reshape(3,3).tolist(),b=d.x[9:].tolist(),loss=float(d.fun)) if d.success else None,
        calibrated_market_confidence=False)


def transform(p,method):
    if method is None:return None
    p=probabilities(p)
    if method['kind']=='raw':return p
    z=np.log(p)
    if method['kind']=='temperature':
        t=float(method['temperature'])
        if not np.isfinite(t) or not .1<=t<=10:raise ValueError('frozen positive bounded temperature required')
        q=softmax(z/t,axis=1)
    elif method['kind']=='dirichlet_identity':
        w=np.asarray(method['w'],float);b=np.asarray(method['b'],float)
        if w.shape!=(3,3) or b.shape!=(3,) or not np.isfinite(w).all() or not np.isfinite(b).all():raise ValueError('typed finite3class Dirichlet map required')
        q=softmax(z@w.T+b,axis=1)
    else:raise ValueError('unregistered calibration method')
    return probabilities(q)


def losses(p,y):
    p=probabilities(p);y=labels(y)
    if len(p)!=len(y):raise ValueError('paired label identity required')
    truth=np.eye(3)[y]
    return dict(log_loss=-np.log(p[np.arange(len(y)),y]),brier=np.sum((p-truth)**2,axis=1))


def select(predictions,y):
    """Select on DISJOINT selection labels only, not calibration fit or validation.

    Frequency is a full candidate. Ordered ties prefer the simpler prior, then
    raw ridge, temperature, Dirichlet, raw tree, temperature, Dirichlet.
    """
    y=labels(y);order=('frequency',)+CANDIDATES[:-1];rows=[]
    if len(y)<30:raise ValueError('selection requires30common labels; no validation rescue')
    common=[k for k in order if predictions.get(k) is not None]
    for name in common:
        l=losses(predictions[name],y)
        rows.append(dict(model=name,n=len(y),log_loss=float(l['log_loss'].mean()),brier=float(l['brier'].mean())))
    if not any(r['model']=='frequency' for r in rows):raise ValueError('prior control required')
    best=min(r['log_loss'] for r in rows)
    winner=next(name for name in order if any(r['model']==name and r['log_loss']<=best+1e-6 for r in rows))
    return dict(winner=winner,ranking=sorted(rows,key=lambda r:(r['log_loss'],order.index(r['model']))),
        criterion='held-selection mean multiclass NLL, simpler within1e-6; no validation labels',
        calibrated_market_confidence=False)
