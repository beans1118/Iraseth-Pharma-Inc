import {useEffect, useId, useRef, useState} from 'react';
import type {QuotationInquiry} from './api';
import './inquiry-decision.css';

type Props = {inquiry: QuotationInquiry; action: 'accept'|'decline'; onCancel: () => void; onConfirm: () => Promise<void>};

export default function InquiryDecision({inquiry, action, onCancel, onConfirm}: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const title = useId(), description = useId();
  const accept = action === 'accept';
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const node = dialog.current!;
    node.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {node.close(); document.body.style.overflow = overflow; previous?.focus();};
  }, []);
  async function submit() {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {await onConfirm();}
    catch (e) {setError(e instanceof Error ? e.message : 'Unable to update inquiry. Please try again.');}
    finally {pending.current = false; setBusy(false);}
  }
  return <dialog ref={dialog} className="inquiry-decision" aria-modal="true" tabIndex={-1} aria-labelledby={title} aria-describedby={description}
    onKeyDown={e => {
      if (e.key !== 'Tab') return;
      const controls = Array.from(e.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled),[tabindex="0"]')).filter(node => node.getClientRects().length > 0);
      if (!controls.length) {e.preventDefault(); e.currentTarget.focus(); return;}
      const first = controls[0], last = controls.at(-1)!;
      if (e.shiftKey && document.activeElement === first) {e.preventDefault(); last.focus();}
      else if (!e.shiftKey && document.activeElement === last) {e.preventDefault(); first.focus();}
    }}
    onCancel={e => {e.preventDefault(); if (!pending.current) onCancel();}}>
    <div className="modal-header"><div><div className="eyebrow">ORDER INQUIRY</div>
      <h2 id={title}>{accept ? 'Accept Order Inquiry?' : 'Decline Order Inquiry?'}</h2></div></div>
    <div className="modal-body" aria-busy={busy}>
      <p className="inquiry-reference">{inquiry.id}</p>
      <div id={description}>{accept ? <><p>Accepting creates one linked Pending Order using current internal order catalog prices.</p>
        <p>Accepting does not reserve or deduct inventory. Approval and fulfillment take place separately in Orders.</p></> :
        <p>This permanently declines the inquiry. No order will be created from it.</p>}</div>
      {error && <p className="form-error" role="alert">{error}</p>}
      {busy && <p role="status">{accept ? 'Creating linked order…' : 'Declining inquiry…'}</p>}
    </div>
    <div className="modal-footer"><button autoFocus className="btn outline" disabled={busy} onClick={onCancel}>Cancel</button>
      <button className={'btn ' + (accept ? 'inquiry-accept' : 'inquiry-decline')} disabled={busy} onClick={() => void submit()}>
        {busy ? 'Please wait…' : accept ? 'Accept & Create Order' : 'Decline Inquiry'}</button></div>
  </dialog>;
}
