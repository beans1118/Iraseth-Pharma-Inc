'use client';
import {useRef, useState, type FormEvent} from 'react';
import Link from 'next/link';
type Tracking = {reference: string; status: string; milestones: Array<{status: string; at: string|null}>};
async function call<T>(data: unknown): Promise<T> {
  const response = await fetch('/api/tracking', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data), cache: 'no-store'});
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Unable to complete this request.');
  return body;
}
export default function TrackOrder({initialReference}: {initialReference: string}) {
  const [reference, setReference] = useState(initialReference), [tracking, setTracking] = useState<Tracking|null>(null);
  const [action, setAction] = useState<'email_update'|'contact'|null>(null), [email, setEmail] = useState(''), [message, setMessage] = useState('');
  const [challenge, setChallenge] = useState(''), [code, setCode] = useState(''), [busy, setBusy] = useState(false), [error, setError] = useState(''), [feedback, setFeedback] = useState('');
  const pending = useRef(false), resultHeading = useRef<HTMLHeadingElement>(null);
  async function work(fn: () => Promise<void>) {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError(''); setFeedback('');
    try {await fn();} catch(e) {setError(e instanceof Error ? e.message : 'Unable to complete request.');}
    finally {pending.current = false; setBusy(false);}
  }
  function reset() {setTracking(null); setAction(null); setChallenge(''); setCode(''); setEmail(''); setMessage(''); setFeedback(''); setError('');}
  async function track(e: FormEvent) {
    e.preventDefault(); reset();
    await work(async () => {setTracking(await call<Tracking>({reference: reference.trim().toUpperCase()})); requestAnimationFrame(() => resultHeading.current?.focus());});
  }
  async function requestCode(e: FormEvent) {
    e.preventDefault();
    await work(async () => {
      const response = await call<{challenge: string; message: string}>({operation: 'request-code', reference: tracking!.reference, email, action, message});
      setChallenge(response.challenge); setFeedback(response.message);
    });
  }
  async function verify(e: FormEvent) {
    e.preventDefault();
    await work(async () => {
      const response = await call<{message: string}>({operation: 'verify-code', challenge, code});
      setFeedback(response.message); setChallenge(''); setAction(null); setCode(''); setEmail(''); setMessage('');
    });
  }
  return <section className="section tracking-section"><div className="container tracking-wrap">
    <p className="eyebrow">YOUR INQUIRY, AT A GLANCE</p><h1>Track My Order</h1>
    <p>Enter your RFQ reference to see its current status. No account is required.</p>
    <form className="tracking-form" onSubmit={track}><label htmlFor="rfq-reference">RFQ reference code</label>
      <div className="tracking-input-row"><input id="rfq-reference" required maxLength={16} pattern="[Rr][Ff][Qq]-[A-Fa-f0-9]{12}" placeholder="RFQ-012345ABCDEF" autoComplete="off" spellCheck={false}
        value={reference} disabled={busy} onChange={e => {setReference(e.target.value); reset();}}/>
        <button className="button button-primary" disabled={busy}>{busy ? 'Please wait…' : 'Track inquiry'}</button></div></form>
    {error && <p role="alert" className="tracking-error">{error}</p>}
    {tracking && <article className="tracking-result" aria-busy={busy}><p className="eyebrow">{tracking.reference}</p>
      <h2 ref={resultHeading} tabIndex={-1}>{tracking.status}</h2>
      <ol className="tracking-milestones" aria-label="Recorded progress">{tracking.milestones.map((step, i) => <li key={i} aria-current={i === tracking.milestones.length - 1 ? 'step' : undefined}>
        <strong>{step.status}</strong>{step.at && <time dateTime={step.at}>{new Date(step.at).toLocaleDateString('en-PH', {year: 'numeric', month: 'short', day: 'numeric'})}</time>}</li>)}</ol>
      <p className="form-note">Only recorded progress is shown. Accepting an inquiry creates a pending order; approval and fulfillment are separate steps.</p>
      <div className="tracking-actions"><button className="button button-primary" disabled={busy} onClick={() => {setAction('email_update'); setChallenge(''); setFeedback('');}}>Request Email Update</button>
        <button className="button button-soft" disabled={busy} onClick={() => {setAction('contact'); setChallenge(''); setFeedback('');}}>Contact Our Team</button></div>
      {action && !challenge && <form className="tracking-communication" onSubmit={requestCode}><h3>{action === 'contact' ? 'Contact our team' : 'Request an email update'}</h3>
        <p>Verify your email before submitting. If it differs from the inquiry email, staff must review your request before sharing any private information.</p>
        <label>Email address<input type="email" required maxLength={254} value={email} disabled={busy} onChange={e => setEmail(e.target.value)}/></label>
        {action === 'contact' && <label>Your message<textarea required maxLength={2000} rows={4} disabled={busy} value={message} onChange={e => setMessage(e.target.value)}/></label>}
        <button className="button button-primary" disabled={busy}>Verify email to continue</button>
        <button type="button" className="button button-soft" disabled={busy} onClick={() => setAction(null)}>Cancel</button></form>}
      {challenge && <form className="tracking-communication" onSubmit={verify}><label>6-digit email verification code<input autoComplete="one-time-code" inputMode="numeric" pattern="[0-9]{6}" required maxLength={6} value={code} disabled={busy} onChange={e => setCode(e.target.value)}/></label>
        <button className="button button-primary" disabled={busy}>Verify & submit request</button></form>}
    </article>}
    {feedback && <p className="tracking-feedback" role="status">{feedback}</p>}
    <p className="form-note">Need help with a reference? <Link className="text-link" href="/contact">Contact Iraseth Pharma</Link>.</p>
  </div></section>;
}
