import {useEffect, useRef, useState} from 'react';
import {api} from './api';
type Request = {id:string;reference:string;email:string;action:string;message:string;ownership:string;status:string;created_at:string};
export default function CommunicationRequests({canWrite}: {canWrite: boolean}) {
  const [items, setItems] = useState<Request[]>([]), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const pending = useRef(false);
  async function load() {try {setItems(await api<Request[]>('/api/v2/communication-requests'));} catch(e) {setError(e instanceof Error ? e.message : 'Unable to load requests.');}}
  useEffect(() => {void load();}, []);
  async function decide(id: string, action: 'close'|'send-update') {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {await api(`/api/v2/communication-requests/${encodeURIComponent(id)}/${action}`, {method:'POST'}); await load();}
    catch(e) {setError(e instanceof Error ? e.message : 'Unable to update request.');}
    finally {pending.current = false; setBusy(false);}
  }
  return <section className="panel" style={{marginBottom:24}}><div className="panel-head"><div><h2>Verified inquiry communication requests</h2>
    <p>Different email addresses require ownership review. Closing a request does not send email.</p></div><button className="btn outline" onClick={() => void load()} disabled={busy}>Refresh requests</button></div>
    {error && <p role="alert" className="form-error">{error}</p>}
    <div style={{padding:20,display:'grid',gap:16}}>{!items.length && <p>No verified requests yet.</p>}{items.map(row => <article className="panel" style={{padding:16}} key={row.id}>
      <strong>{row.reference} · {row.action === 'email_update' ? 'Email update' : 'Contact request'}</strong><p>{row.email} · {row.status}</p>
      <p>{row.ownership === 'original_email' ? 'Original inquiry email verified' : 'Different email verified — ownership unconfirmed. Review through your established customer verification process; do not share private details.'}</p>
      {row.message && <p>{row.message}</p>}{canWrite && ['queued','needs_review'].includes(row.status) && <div className="row-actions">
        {row.ownership === 'original_email' && <button className="btn primary" disabled={busy} onClick={() => void decide(row.id,'send-update')}>Send Status Update</button>}
        <button className="btn outline" disabled={busy} onClick={() => void decide(row.id,'close')}>Close request</button></div>}</article>)}</div></section>;
}
