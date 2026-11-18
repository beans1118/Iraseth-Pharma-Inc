export type BrochureSelection={candidate_id:string;id:string;unit:string;review_confirmed:boolean;review_notes:string;duplicate_reviewed:boolean;include_images:boolean;images_reviewed:boolean;model_decision:string;model:string;model_evidence:string;image_decision:string};
type Candidate={candidate_id:string;source_ready:boolean;existing_identity_count:number};

export function parseMappingCsv(text:string):Record<string,string>[] {
  const rows:string[][]=[];let row:string[]=[],cell='',quoted=false;
  text=text.replace(/^\uFEFF/,'');
  for(let i=0;i<text.length;i++){
    const ch=text[i];
    if(quoted){if(ch==='"'){if(text[i+1]==='"'){cell+='"';i++;}else quoted=false;}else cell+=ch;}
    else if(ch==='"'){if(cell)throw new Error('Invalid CSV quoting.');quoted=true;}
    else if(ch===','){row.push(cell);cell='';}
    else if(ch==='\n'||ch==='\r'){if(ch==='\r'&&text[i+1]==='\n')i++;row.push(cell);if(row.some(Boolean))rows.push(row);row=[];cell='';}
    else cell+=ch;
  }
  if(quoted)throw new Error('CSV contains an unclosed quoted cell.');
  if(cell||row.length){row.push(cell);if(row.some(Boolean))rows.push(row);}
  const header=rows.shift();if(!header||new Set(header).size!==header.length)throw new Error('CSV headers are missing or duplicated.');
  for(const key of ['candidate_id','include_in_batch','staff_approved_sku','staff_approved_selling_unit','model_decision','image_decision','staff_approved'])
    if(!header.includes(key))throw new Error('Download the current mapping template; missing column: '+key);
  return rows.map(values=>{if(values.length!==header.length)throw new Error('CSV row has the wrong number of columns.');return Object.fromEntries(header.map((key,i)=>[key,values[i]]));});
}

function flag(value:string|undefined){if(!value||value.toLowerCase()==='false')return false;if(value.toLowerCase()==='true')return true;throw new Error('Approval and batch flags must be true or false.');}
export function mappingDraft(text:string,candidates:Candidate[]):Record<string,BrochureSelection> {
  const byId=new Map(candidates.map(row=>[row.candidate_id,row])),seen=new Set<string>(),skus=new Set<string>(),result:Record<string,BrochureSelection>={};
  for(const row of parseMappingCsv(text)){
    const id=row.candidate_id;if(seen.has(id))throw new Error('Duplicate candidate in CSV: '+id);seen.add(id);
    const candidate=byId.get(id);if(!candidate)throw new Error('Unknown candidate key in CSV: '+id);
    if(!flag(row.include_in_batch))continue;
    if(!candidate.source_ready||candidate.existing_identity_count)throw new Error('This candidate is blocked or already exists: '+id);
    const sku=row.staff_approved_sku.trim(),canonical=sku.normalize('NFKC').toLowerCase();
    if(canonical&&skus.has(canonical))throw new Error('Duplicate SKU in selected CSV rows: '+sku);if(canonical)skus.add(canonical);
    const model_decision=row.model_decision||'pending',image_decision=row.image_decision||'pending';
    if(!['pending','use_documented','not_documented','staff_verified'].includes(model_decision)||!['pending','include','omit'].includes(image_decision))throw new Error('Invalid model or image decision in CSV.');
    result[id]={candidate_id:id,id:sku,unit:row.staff_approved_selling_unit.trim(),review_confirmed:flag(row.staff_approved),review_notes:row.staff_review_notes||'',
      duplicate_reviewed:flag(row.duplicate_reviewed),model_decision,model:row.staff_verified_model||'',model_evidence:row.model_evidence||'',
      image_decision,include_images:image_decision==='include',images_reviewed:flag(row.images_approved)};
  }
  const count=Object.keys(result).length;if(!count||count>30)throw new Error('Mark 1 to 30 rows include_in_batch=true; start with 1 to 5.');
  return result;
}
