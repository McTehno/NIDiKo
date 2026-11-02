import csv
import argparse
import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser=argparse.ArgumentParser(description='Izračun dokaznih statistik in grafov zaključenega vzdržljivostnega testa.')
parser.add_argument('--run',type=Path,required=True)
parser.add_argument('--generator',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
RUN=args.run.resolve()
OUT=args.output.resolve()
manifest=json.loads((RUN/'manifest.json').read_text(encoding='utf-8'))
ASSETS=OUT/'assets'
ASSETS.mkdir(parents=True,exist_ok=True)
rows=[json.loads(line) for line in (RUN/'events.jsonl').open(encoding='utf-8')]
schedule=next(r for r in rows if r['kind']=='schedule')
start,end=schedule['steady_start'],schedule['steady_end']
requests=[r for r in rows if r['kind']=='request']
steady=[r for r in requests if r['phase']=='steady']
population=[r for r in rows if r['kind']=='population' and r['phase']=='steady']

def percentile(values,q):
    s=sorted(values)
    return s[max(0,math.ceil(len(s)*q)-1)]

def stats(values):
    return {'min':min(values),'max':max(values),'mean':statistics.mean(values),'p95':percentile(values,.95)}

def group_stats(events):
    groups=defaultdict(list)
    for r in events:groups[r['group']].append(r)
    result={}
    for name,group in groups.items():
        limit=400 if name.startswith('ordinary/') else 7000 if name=='ai' else 3000
        ms=[r['ms'] for r in group]
        success=[r for r in group if r['ok']]
        result[name]={'count':len(group),'failed':len(group)-len(success),
            'success_percent':len(success)/len(group)*100,
            'fast_percent':sum(r['ok'] and r['ms']<=limit for r in group)/len(group)*100,
            'slow_successes':sum(r['ok'] and r['ms']>limit for r in group),
            'mean_ms':statistics.mean(ms),'median_ms':percentile(ms,.5),
            'p95_ms':percentile(ms,.95),'p99_ms':percentile(ms,.99),'max_ms':max(ms)}
    return result

csvrows=list(csv.DictReader((RUN/'locust_stats.csv').open(encoding='utf-8')))
assert int(next(r for r in csvrows if r['Name']=='Aggregated')['Request Count'])==len(requests)
assert int(next(r for r in csvrows if r['Name']=='Aggregated')['Failure Count'])==sum(not r['ok'] for r in requests)
gaps=[b['time']-a['time'] for a,b in zip(population,population[1:])]
host=list(csv.DictReader((RUN/'infrastructure/host.csv').open(encoding='utf-8')))
backend=[]
for line in (RUN/'infrastructure/containers.jsonl').open(encoding='utf-8'):
    r=json.loads(line)
    if r['stats']['Name']!='nidiko_backend':continue
    t=datetime.fromisoformat(r['utc'].replace('Z','+00:00')).timestamp()
    value,unit=re.match(r'([\d.]+)(\w+)',r['stats']['MemUsage']).groups()
    mib=float(value)*({'MiB':1,'GiB':1024,'KiB':1/1024,'B':1/1024**2}[unit])
    backend.append({'time':t,'cpu':float(r['stats']['CPUPerc'].rstrip('%')),'mib':mib})
states=[json.loads(l) for l in (RUN/'infrastructure/container-state.jsonl').open(encoding='utf-8')]
backend_states=[r for r in states if r['container']['Names']=='nidiko_backend']
steady_backend=[r for r in backend if start<=r['time']<=end]
steady_host=[r for r in host if start<=datetime.fromisoformat(r['utc'].replace('Z','+00:00')).timestamp()<=end]
generator=[json.loads(l) for l in args.generator.open(encoding='utf-8')]
times=[datetime.fromisoformat(r['utc']).timestamp() for r in generator]
hours=[]
duration_hours=(end-start)/3600
for h in range(math.ceil(duration_hours)):
    samples=[r for r in steady if start+h*3600<=r['time']<start+(h+1)*3600]
    hours.append({'hour':h+1,'count':len(samples),'failures':sum(not r['ok'] for r in samples),'groups':group_stats(samples)})
metrics={'run_id':manifest['run_id'],'steady_start_utc':datetime.fromtimestamp(start,timezone.utc).isoformat(),
    'steady_end_utc':datetime.fromtimestamp(end,timezone.utc).isoformat(),
    'steady_duration_seconds':end-start,'all_request_count':len(requests),'steady_request_count':len(steady),
    'all_success_percent':100*sum(r['ok'] for r in requests)/len(requests),'steady_success_percent':100*sum(r['ok'] for r in steady)/len(steady),
    'steady_rps':len(steady)/(end-start),'max_population_gap_seconds':max(gaps),
    'population_values':sorted({r['users'] for r in population}),
    'all_groups':group_stats(requests),'steady_groups':group_stats(steady),
    'hours':hours,
    'failures':[{'utc':datetime.fromtimestamp(r['time'],timezone.utc).isoformat(),'group':r['group'],'ms':r['ms']} for r in requests if not r['ok']],
    'backend_memory_mib':stats([r['mib'] for r in steady_backend]),
    'backend_cpu_docker_percent':stats([r['cpu'] for r in steady_backend]),
    'backend_first10min_mean_mib':statistics.mean(r['mib'] for r in steady_backend if r['time']<start+600),
    'backend_last10min_mean_mib':statistics.mean(r['mib'] for r in steady_backend if r['time']>=end-600),
    'backend_recovery_memory_mib':[r['mib'] for r in backend if r['time']>end],
    'host_available_gib':stats([int(r['mem_available_kb'])/1024**2 for r in steady_host]),
    'host_load1':stats([float(r['load1']) for r in steady_host]),
    'host_disk_available_gib':stats([int(r['disk_available_kb'])/1024**2 for r in steady_host]),
    'backend_container_ids':sorted({r['container']['ID'] for r in backend_states}),
    'backend_state_values':dict(Counter(r['container']['State'] for r in backend_states)),
    'generator_cpu_percent':stats([r['cpu_percent'] for r in generator]),
    'generator_max_gap_seconds':max(b-a for a,b in zip(times,times[1:])),
    'generator_memory_percent':stats([r['memory_percent'] for r in generator])}
(ASSETS/'metrics.json').write_text(json.dumps(metrics,indent=2,ensure_ascii=False),encoding='utf-8')

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
summary=json.loads((RUN/'summary.json').read_text(encoding='utf-8'))
fig,axes=plt.subplots(3,1,figsize=(10,9),layout='constrained',sharex=True)
sets=[(['ordinary/questionnaire','ordinary/evaluate'],['Pridobitev','Oddaja'],400),
      (['ai'],['AI pomočnik'],7000),(['voice_cached','voice_audio'],['Glasovni API (predpomnilnik)','Prenos zvoka'],3000)]
for ax,(names,labels,limit) in zip(axes,sets):
    for name,label in zip(names,labels):
        window_minutes=manifest['profile']['window_seconds']/60
        points=[((int(i)+.5)*window_minutes,w[name]['p99_ms']) for i,w in summary['windows'].items() if name in w]
        ax.plot([p[0]/60 for p in points],[p[1] for p in points],label=label,linewidth=1.5)
    ax.axhline(limit,color='#b42318',linestyle='--',label=f'Časovna meja {limit} ms')
    ax.set_ylabel('p99 [ms]');ax.grid(alpha=.2);ax.legend(loc='upper right',fontsize=8)
axes[-1].set_xlabel('Čas od začetka ciljne faze [h]')
fig.suptitle('NIDiKo — p99 po 5-minutnih intervalih ciljne faze\nGlasovni intervali imajo majhno število vzorcev; p99 ni merilo vseh zahtev AI.')
fig.savefig(ASSETS/'odzivni-casi.png',dpi=160);plt.close(fig)

fig,axes=plt.subplots(4,1,figsize=(10,10),layout='constrained',sharex=True)
x=[(r['time']-start)/3600 for r in backend]
axes[0].plot(x,[r['mib'] for r in backend],color='#175cd3');axes[0].set_ylabel('Backend RAM\n[MiB]')
axes[1].plot(x,[r['cpu'] for r in backend],color='#027a48',linewidth=.7);axes[1].set_ylabel('CPU Docker\n[%; 200 % = 2 jedri]')
ht=[(datetime.fromisoformat(r['utc'].replace('Z','+00:00')).timestamp()-start)/3600 for r in host]
axes[2].plot(ht,[int(r['mem_available_kb'])/1024**2 for r in host]);axes[2].set_ylabel('Razpoložljivi RAM\ngostitelja [GiB]')
pop=[r for r in rows if r['kind']=='population']
axes[3].plot([(r['time']-start)/3600 for r in pop],[r['users'] for r in pop]);axes[3].set_ylabel('Izmerjena\naktivna mesta');axes[3].set_ylim(0,110)
for ax in axes:
    ax.axvspan(0,duration_hours,color='#ecfdf3',zorder=-5,label='Ciljna faza')
    ax.axvline(duration_hours,color='#b42318',linestyle='--',linewidth=1)
    ax.grid(alpha=.2)
axes[-1].set_xlabel('Čas glede na začetek ciljne faze [h]; črtkano: konec obremenitve')
fig.suptitle('NIDiKo — infrastruktura in časovno pokritje\nZadnji dve minuti: okrevanje; populacija je narisana samo tam, kjer je izmerjena.')
fig.savefig(ASSETS/'infrastruktura.png',dpi=160);plt.close(fig)

hashes=[]
for p in sorted(RUN.rglob('*')):
    if p.is_file():hashes.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(RUN).as_posix())
(ASSETS/'SHA256SUMS-run.txt').write_text('\n'.join(hashes)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in metrics.items() if k not in ('hours','all_groups','steady_groups','backend_recovery_memory_mib')},indent=2))
print('recovery_memory',metrics['backend_recovery_memory_mib'][:3],metrics['backend_recovery_memory_mib'][-3:])
print('hourly_counts',[(r['hour'],r['count'],r['failures']) for r in hours])
