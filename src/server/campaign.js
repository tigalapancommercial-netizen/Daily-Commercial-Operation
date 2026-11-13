// Campaign data is scoped to the authenticated DCO session in SECURITY DEFINER SQL.
// All Date/Month/Year/range history queries are verified server-side and paginated.
export async function list_(ctx) { return ctx.call('dco_campaign_list'); }
export async function detail_(ctx,p={}) {
  if(!p.id) throw new Error('Pilih campaign terlebih dahulu');
  return ctx.call('dco_campaign_detail',{p_campaign_id:p.id,p_store:p.toko||null,p_from:p.from||null,p_to:p.to||null});
}
export async function records_(ctx,p={}) {
  if(!p.id) throw new Error('Pilih campaign terlebih dahulu');
  return ctx.call('dco_campaign_records',{p_campaign_id:p.id,p_store:p.toko||null,p_kind:p.kind||null,
    p_from:p.from||null,p_to:p.to||null,p_limit:Math.max(1,Math.min(200,Number(p.limit)||100)),p_offset:Math.max(0,Number(p.offset)||0)});
}
export async function save_(ctx,p={}) {
  if(!ctx.me.isMgr) throw new Error('Pengelolaan campaign hanya untuk Master/SPV');
  return ctx.call('dco_campaign_save',{p_data:p.data||{}});
}
export async function recordSave_(ctx,p={}) {
  if(!p.id || !p.kind) throw new Error('Campaign dan jenis input wajib dipilih');
  return ctx.call('dco_campaign_record_save',{p_campaign_id:p.id,p_kind:p.kind,p_data:p.data||{}});
}
