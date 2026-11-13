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

// v19: Campaign lifecycle. All destructive operations are validated again by SQL for MASTER.
import { sb, BUCKET, STORAGE_PATH_RE } from '../db.js';
export async function trashList_(ctx) {
  if (!ctx.me.isMaster) throw new Error('Sampah Campaign hanya untuk Master');
  return ctx.call('dco_campaign_trash_list');
}
export async function deletePreview_(ctx,p={}) {
  if (!ctx.me.isMaster) throw new Error('Hanya Master');
  if (!p.id) throw new Error('Pilih campaign');
  return ctx.call('dco_campaign_delete_preview',{p_campaign_id:p.id});
}
export async function backupSection_(ctx,p={}) {
  if (!ctx.me.isMaster) throw new Error('Backup lengkap Campaign hanya untuk Master');
  if (!p.id) throw new Error('Pilih campaign');
  return ctx.call('dco_campaign_export_section',{
    p_campaign_id:p.id,p_section:p.section||'records',
    p_limit:Math.max(1,Math.min(500,Number(p.limit)||200)),
    p_offset:Math.max(0,Number(p.offset)||0)
  });
}
export async function manage_(ctx,p={}) {
  if (!ctx.me.isMaster) throw new Error('Hanya Master yang dapat menghapus/memulihkan Campaign');
  if (!p.id || !['trash','restore','purge'].includes(p.action)) throw new Error('Pilihan aksi Campaign tidak valid');
  const r=await ctx.call('dco_campaign_manage',{
    p_campaign_id:p.id,p_action:p.action,p_confirm_name:p.confirmName||null,
    p_backup_ack:!!p.backupAck
  });
  // Cleanup is a separate optional operation. Database deletion already committed;
  // failed Storage requests are queued and can be retried later, not concealed.
  return r;
}
export async function cleanupCount_(ctx){
  if (!ctx.me.isMaster) throw new Error('Hanya Master');
  return ctx.call('dco_campaign_cleanup_count');
}
export async function cleanup_(ctx,p={}){
  if (!ctx.me.isMaster) throw new Error('Hanya Master yang dapat membersihkan foto');
  if (!sb) throw new Error('Supabase belum dikonfigurasi');
  const prepared=await ctx.call('dco_campaign_cleanup_prepare',{p_limit:Math.max(1,Math.min(30,Number(p.limit)||20))});
  const paths=(prepared.paths||[]).filter(x=>STORAGE_PATH_RE.test(String(x)));
  let removed=0, failed=0;const confirmed=[];const reasons=[];
  for(const path of paths){
    try{
      const {data,error}=await sb.storage.from(BUCKET).remove([path]);
      if(error)throw error;
      if(!Array.isArray(data)||!data.some(d=>(d.name||d.path)===path))throw new Error('Storage tidak mengonfirmasi file dihapus');
      confirmed.push(path);removed++;
    }catch(e){failed++;reasons.push(String(e?.message||e).slice(0,150));}
  }
  if(confirmed.length)await ctx.call('dco_campaign_cleanup_confirm',{p_paths:confirmed});
  return {removed,failed,pending:Math.max(0,(Number(prepared.pending)||0)-removed),
    message:failed?'Sebagian foto belum terhapus; dapat dicoba ulang. '+reasons[0]:'Foto kandidat berhasil dibersihkan.'};
}
