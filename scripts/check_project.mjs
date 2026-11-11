import {existsSync,readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname,resolve} from 'node:path';
const root=resolve(dirname(fileURLToPath(import.meta.url)),'..');
let failure=0;
for(const file of ['index.html','src/main.js','src/data.js','src/constants.js','src/styles.css','supabase/migrations/20261111_001_initial.sql','supabase/migrations/20261111_002_full_operations.sql','supabase/migrations/20261111_003_security_and_briefing.sql','supabase/migrations/20261111_004_integrity.sql','supabase/migrations/20261111_005_storage_maintenance.sql','docs/INSTALL_GITHUB_SUPABASE.md']){
 if(!existsSync(resolve(root,file))){console.error('MISSING',file);failure++;}
}
const pkg=JSON.parse(readFileSync(resolve(root,'package.json')));
if(!pkg.dependencies['@supabase/supabase-js']){console.error('Missing Supabase client');failure++;}
for(const file of ['src/main.js','src/data.js']){
 const t=readFileSync(resolve(root,file),'utf-8');
 if(/google\.script\.run|SpreadsheetApp|DriveApp/.test(t)){console.error('Unexpected Google Apps Script runtime in',file);failure++;}
}
if(failure)process.exit(1);
console.log('PASS: required project files, Supabase client and no Google Apps Script runtime.');
