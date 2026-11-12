import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
const site=fileURLToPath(new URL('../site/', import.meta.url)).replace(/\/$/,'');
globalThis.fetch=async(input)=>{
 const url=new URL(typeof input==='string'?input:input.url??input.toString(),'http://localhost');
 const file=resolve(site,url.pathname.replace(/^\/mailinglisten-archiv\//,''));
 if(!file.startsWith(site+'/'))throw Error('Unexpected fetch '+file);
 const data=await readFile(file);
 return new Response(data,{headers:{'Content-Type':file.endsWith('.wasm')?'application/wasm':'application/octet-stream'}});
};
const module=await import(pathToFileURL(site+'/pagefind/pagefind.js'));
const api=module.createInstance({basePath:'/mailinglisten-archiv/pagefind/',baseUrl:'/mailinglisten-archiv/'});
const filters=await api.filters();
if(!filters.Liste?.['tyndur-devel']||!filters.Liste?.['cdi-devel'])throw Error('Missing list filters');
for(const [term,options] of [['lostio',{}],['CDI',{filters:{Liste:'cdi-devel',Jahr:'2010'}}],['SDL',{}],['strtoxxx',{filters:{Liste:'tyndur-devel',Jahr:'2021'}}]]){
 const results=await api.search(term,options);
 if(!results.results.length)throw Error('No results for '+term);
 const first=await results.results[0].data();
 if(!first.url.startsWith('/mailinglisten-archiv/'))throw Error('Wrong URL prefix '+first.url);
 const url=new URL(first.url,'http://localhost');
 await readFile(site+url.pathname.replace(/^\/mailinglisten-archiv/,''),'utf8');
 if(options.filters&&Object.entries(options.filters).some(([key,value])=>!first.filters[key].includes(value)))throw Error('Filters not applied');
 console.log(JSON.stringify({term,matches:results.results.length,first:first.url,filters:first.filters}));
}
await api.destroy();
