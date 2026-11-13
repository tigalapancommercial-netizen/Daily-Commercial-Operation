// Weekly and monthly reports live in dco.period_reports; no Apps Script dependency.
// Authorization and store isolation enforced by SQL SECURITY DEFINER RPC.
export async function list_(ctx, p = {}) {
  return ctx.call('dco_period_list', {
    p_type: p.type || null,
    p_store: p.toko && p.toko !== 'SEMUA' ? p.toko : null,
    p_from: p.from || null,
    p_to: p.to || null,
    p_limit: Math.min(200, Math.max(1, Number(p.limit) || 100)),
    p_offset: Math.max(0, Number(p.offset) || 0),
  });
}
export async function submit_(ctx, p = {}) {
  return ctx.call('dco_period_submit', {
    p_type: String(p.type || ''),
    p_store: ctx.me.isMgr ? String(p.toko || '') : ctx.me.toko,
    p_report_date: String(p.date || ''),
    p_payload: p.payload || {},
    p_evidence: p.evidence || {},
  });
}
export async function validate_(ctx, p = {}) {
  if (!ctx.me.isMgr) throw new Error('Hanya SPV Area atau Master yang boleh melakukan validasi');
  return ctx.call('dco_period_validate', {
    p_id: p.id,
    p_action: p.action,
    p_note: p.note || '',
  });
}
export async function summary_(ctx, p = {}) {
  return ctx.call('dco_period_summary', { p_date: p.date || null });
}
