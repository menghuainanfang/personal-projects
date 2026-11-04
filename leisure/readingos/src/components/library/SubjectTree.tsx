import {useTree} from '@headless-tree/react';
import {syncDataLoaderFeature,selectionFeature,hotkeysCoreFeature,searchFeature} from '@headless-tree/core';
import {useEffect,useState} from 'react';
import {subjectBooks,subjectPath} from '../../../shared/library.mjs';
import type {Snapshot} from '../../domain';
export function SubjectTree({data,selected,onSelect}:{data:Snapshot;selected:string;onSelect:(id:string)=>void}){
 const [search,setSearch]=useState<string|null>(null);
 const tree=useTree<{name:string}>({rootItemId:'root',state:{selectedItems:selected?[selected]:[],search},setSearch,
  getItemName:item=>item.getItemData().name,isItemFolder:()=>true,
  dataLoader:{getItem:id=>({name:data.subject_categories.find(c=>c.id===id)?.name||'学科'}),getChildren:id=>data.subject_categories.filter(c=>c.parent_id===(id==='root'?null:id)).sort((a,b)=>a.sort_order-b.sort_order||a.name.localeCompare(b.name,'zh-CN')).map(c=>c.id)},
  setSelectedItems:next=>{const value=typeof next==='function'?next(selected?[selected]:[]):next;if(value[0])onSelect(value[0]);},
  isSearchMatchingItem:(value,item)=>subjectPath(data.subject_categories,item.getId()).toLowerCase().includes(value.toLowerCase()),
  features:[syncDataLoaderFeature,selectionFeature,hotkeysCoreFeature,searchFeature]});
 useEffect(()=>{tree.rebuildTree();},[data.subject_categories,tree]);
 return <><label>查找学科路径<input {...tree.getSearchInputElementProps()} aria-label="查找学科路径" value={search||''} onChange={e=>{tree.setSearch(e.target.value);for(const c of data.subject_categories)tree.getItemInstance(c.id).expand();}}/></label><div {...tree.getContainerProps()} aria-label="学科目录" className="subject-tree">{tree.getItems().map(item=><button {...item.getProps()} type="button" key={item.getId()} style={{paddingInlineStart:10+item.getItemMeta().level*16}} className={item.isSelected()?'selected':''} data-match={item.isMatchingSearch()||undefined}><span aria-hidden>{item.isExpanded()?'▾':'▸'}</span><span>{item.getItemName()}</span><small>{subjectBooks(data,item.getId()).size}</small></button>)}</div></>;
}
