import {useEffect,useMemo,useState} from 'react';
import {endpoints,type AnalyticsOverview,type InvoiceTransaction,type Movement} from './api';
import './reports.css';

const fmt=(value:number)=>new Intl.NumberFormat('en-PH',{maximumFractionDigits:2}).format(value);
const when=(value?:string)=>value&&!Number.isNaN(Date.parse(value))?new Date(value).toLocaleString('en-PH'):'—';
const title=(value:string)=>value.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());

function ExportCSV({rows,filename}:{rows:string[][];filename:string}){
 function download(){const csv=rows.map(line=>line.map(v=>`"${String(v).replaceAll('"','""')}"`).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob(['\uFEFF',csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 return <button type="button" className="btn outline" onClick={download}>Export CSV</button>;
}
function Warning({message}:{message:string}){return <div role="alert" className="report-error">{message}</div>}

export function TransactionReports(){
 const [tab,setTab]=useState<'stock'|'invoice'>('stock');
 const [stock,setStock]=useState<Movement[]>([]),[events,setEvents]=useState<InvoiceTransaction[]>([]);
 const [stockError,setStockError]=useState(''),[invoiceError,setInvoiceError]=useState('');
 const [query,setQuery]=useState(''),[loading,setLoading]=useState(true);
 const [reload,setReload]=useState(0);
 useEffect(()=>{let live=true;setLoading(true);setStockError('');setInvoiceError('');Promise.allSettled([endpoints.movements(),endpoints.invoiceTransactions()]).then(results=>{if(!live)return;
   if(results[0].status==='fulfilled')setStock(results[0].value);else {setStock([]);setStockError(results[0].reason instanceof Error?results[0].reason.message:'Unable to load stock movements')}
   if(results[1].status==='fulfilled')setEvents(results[1].value);else {setEvents([]);setInvoiceError(results[1].reason instanceof Error?results[1].reason.message:'Unable to load invoice events')}
   setLoading(false);
 });return()=>{live=false}},[reload]);
 const q=query.toLowerCase().trim();
 const stockRows=stock.filter(x=>`${x.product_id} ${x.action||x.type} ${x.actor_email} ${x.reference||''}`.toLowerCase().includes(q));
 const invoiceRows=events.filter(x=>`${x.invoice_id} ${x.event} ${x.actor_email}`.toLowerCase().includes(q));
 const rows=tab==='stock'?[['Date','Action','Product ID','Quantity','Staff','Reference'],...stockRows.map(m=>[m.at||'',m.action||m.type||'',m.product_id||'',String(m.qty??''),m.actor_email||'',m.reference||''])]:[['Date','Invoice ID','Event','Staff'],...invoiceRows.map(e=>[e.at,e.invoice_id,e.event,e.actor_email])];
 return <section className="phase3-report" aria-label="Transaction records">
  <div className="report-controls"><div className="report-tabs"><button aria-pressed={tab==='stock'} onClick={()=>setTab('stock')}>Inventory Movements</button><button aria-pressed={tab==='invoice'} onClick={()=>setTab('invoice')}>Invoice Activity</button></div><div className="report-filter"><input aria-label="Search transactions" placeholder="Search records..." value={query} onChange={e=>setQuery(e.target.value)}/><button className="btn outline" onClick={()=>setReload(v=>v+1)}>Reload</button><ExportCSV filename={`iraseth-${tab}-records.csv`} rows={rows}/></div></div>
  {loading&&<p className="report-muted">Loading records…</p>}
  {!loading&&(tab==='stock'?stockError:invoiceError)&&<Warning message={`${tab==='stock'?'Inventory movements':'Invoice activity'} could not load: ${tab==='stock'?stockError:invoiceError}. Check the running Flask backend and permissions.`}/>}
  <div className="report-table-wrap"><table><thead><tr>{(tab==='stock'?['Date','Action','Product ID','Quantity','Staff','Reference']:['Date','Invoice ID','Event','Staff']).map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{tab==='stock'?stockRows.map((m,i)=><tr key={m.id||i}><td>{when(m.at)}</td><td>{title(m.action||m.type||'—')}</td><td>{m.product_id||'—'}</td><td>{m.qty??'—'}</td><td>{m.actor_email||'—'}</td><td>{m.reference||'—'}</td></tr>):invoiceRows.map((e,i)=><tr key={e.id||i}><td>{when(e.at)}</td><td>{e.invoice_id}</td><td>{title(e.event)}</td><td>{e.actor_email}</td></tr>)}</tbody></table>{!loading&&!(tab==='stock'?stockError:invoiceError)&&rows.length===1&&<p className="report-empty">No matching records.</p>}</div>
  <p className="report-note">Showing recent records. CSV exports only the currently loaded and filtered records.</p>
 </section>;
}

function BarBreakdown({heading,values}:{heading:string;values:Record<string,number>}){
 const entries=Object.entries(values).sort((a,b)=>b[1]-a[1]);const max=Math.max(1,...entries.map(([,v])=>v));
 return <article className="report-chart-card"><h3>{heading}</h3>{entries.length===0?<p className="report-muted">No records yet.</p>:<div className="report-bar-list">{entries.map(([name,value])=><div className="report-bar-row" key={name}><div className="report-bar-label"><span>{title(name)}</span><strong>{fmt(value)}</strong></div><div className="report-bar-track"><div className="report-bar-fill" style={{width:`${Math.max(0,Math.min(100,value/max*100))}%`}}/></div></div>)}</div>}</article>;
}
function TrendChart({data,days}:{data:AnalyticsOverview['movement_trends'];days:number}){
 const group=new Map<string,number>();for(const row of data)group.set(row.day,(group.get(row.day)||0)+Math.abs(row.units));
 const entries=[...group].sort((a,b)=>a[0].localeCompare(b[0]));const top=Math.max(1,...entries.map(([,n])=>n));
 return <article className="report-chart-card report-wide-chart"><h3>Stock Movements · Last {days} Days</h3><p className="report-muted">Movement quantity grouped by day. Product units may differ.</p>{entries.length===0?<div className="report-empty-chart">No movement data for this period.</div>:<div className="report-chart-scroll"><div className="report-vertical-chart" role="img" aria-label="Daily inventory movement quantities">{entries.map(([day,value])=><div className="report-vcol" key={day} title={`${day}: ${fmt(value)} units`}><span className="report-vvalue">{fmt(value)}</span><div className="report-vbar" style={{height:`${Math.max(3,value/top*100)}%`}}/><span className="report-vdate">{day.slice(5)}</span></div>)}</div></div>}</article>;
}
export function AnalyticsReports(){
 const [days,setDays]=useState<7|30|90>(30),[data,setData]=useState<AnalyticsOverview|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState(''),[reload,setReload]=useState(0);
 useEffect(()=>{let live=true;setLoading(true);setError('');endpoints.analyticsOverview(days).then(v=>{if(live)setData(v)}).catch(e=>{if(live){setData(null);setError(e instanceof Error?e.message:'Unable to load analytics')}}).finally(()=>{if(live)setLoading(false)});return()=>{live=false}},[days,reload]);
 const cards=useMemo(()=>data?[{label:'Catalog Products',value:data.products,subtitle:'All product records'},{label:'On-hand Units',value:data.on_hand,subtitle:'Across all batches'},{label:'Reserved Units',value:data.reserved,subtitle:'Allocated to orders'},{label:'Eligible Available',value:data.available_eligible,subtitle:'Excludes restricted stock'},{label:'Expiring Batches',value:data.expiring_batches_90d,subtitle:'Next 90 days'},{label:'Tracked Batches',value:data.batch_count,subtitle:'Total inventory batches'}]:[],[data]);
 return <section className="phase3-report" aria-label="Analytics dashboard"><div className="report-controls report-analytics-tools"><span className="report-muted">Live inventory and operational reporting</span><div className="report-filter"><label>Movement period <select value={days} onChange={e=>setDays(Number(e.target.value) as 7|30|90)}><option value={7}>7 days</option><option value={30}>30 days</option><option value={90}>90 days</option></select></label><button className="btn outline" onClick={()=>setReload(v=>v+1)}>Reload</button></div></div>
 {loading&&<p className="report-muted">Loading analytics…</p>}
 {error&&<Warning message={`Analytics could not load: ${error}. A “Not found” response usually means the Flask analytics route is not registered in the running backend. Restart Flask and check /api/v2/analytics/overview?days=30.`}/>}
 {data&&<><div className="report-cards">{cards.map(card=><article className="report-stat" key={card.label}><span>{card.label}</span><strong>{fmt(card.value)}</strong><small>{card.subtitle}</small></article>)}</div><div className="report-chart-grid"><TrendChart data={data.movement_trends} days={days}/><BarBreakdown heading="Orders by Status" values={data.orders_by_status}/><BarBreakdown heading="Invoices by Status" values={data.invoices_by_status}/></div><p className="report-note">{data.scope_note} As of {when(data.as_of_utc)}. Stock snapshot values are not restricted to the selected movement period. These counts do not represent revenue or inventory valuation.</p></>}
 </section>;
}
