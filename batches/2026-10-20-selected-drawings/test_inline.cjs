const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[2]||'/workspace/cartoon-archive-selected-drawings.html','utf8');
const code=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const data=JSON.parse(code.match(/data=(.*);\nconst subject=/)[1]);
function node(value=''){return{value,src:'',textContent:'',listeners:{},attrs:{},append(x){(this.children??=[]).push(x);},setAttribute(k,v){this.attrs[k]=v;},addEventListener(t,f){this.listeners[t]=f;}};}
const nodes={subject:node('0'),revision:node('selected'),photo:node(),art:node(),'art-label':node(),time:node(),detail:node()};
const keys=Array.from({length:4},(_,i)=>Object.assign(node(),{dataset:{key:String(i)}}));
const root={querySelector(q){return nodes[q.match(/data-([^\]]+)/)[1]];},querySelectorAll:()=>keys};
vm.runInNewContext(code,{document:{getElementById:()=>root,createElement:()=>node()},console});
assert.equal(nodes.subject.children.length,10);
for(let i=0;i<10;i++){
 nodes.subject.value=String(i);nodes.subject.listeners.change();
 for(let k=0;k<4;k++){
  keys[k].listeners.click();assert.equal(nodes.photo.src,data.items[i].photos[k]);
  nodes.revision.value='selected';nodes.revision.listeners.change();assert.equal(nodes.art.src,data.items[i].selected[k]);
  nodes.revision.value='first';nodes.revision.listeners.change();assert.equal(nodes.art.src,data.items[i].first[k]);
  assert.equal(keys[k].attrs['aria-pressed'],'true');
 }
}
assert.equal(root.drawingRepairs.getState().itemIndex,9);assert(Buffer.byteLength(html)<1000000);assert(!/fetch\(|XMLHttpRequest|WebSocket/.test(code));
console.log(JSON.stringify({passed:true,subjects:10,pose_pairs:40,revision_pairs:80,scope:'DOM-stub interaction test, not browser layout or normal-speed video review'}));
