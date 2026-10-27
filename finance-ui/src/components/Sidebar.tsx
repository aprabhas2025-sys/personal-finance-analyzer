import { Activity, AlertTriangle, ArrowLeftRight, Bot, ChevronRight, CircleDollarSign, CreditCard, LayoutDashboard, Repeat2, Settings2, Sparkles, WalletCards } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

const nav: {title:string;items:{label:string;icon:LucideIcon}[]}[]=[
 {title:'Workspace',items:[{label:'Overview',icon:LayoutDashboard},{label:'Transactions',icon:ArrowLeftRight},{label:'Anomalies',icon:AlertTriangle},{label:'Subscriptions',icon:Repeat2},{label:'Forecast',icon:Activity}]},
 {title:'Analysis',items:[{label:'By category',icon:CircleDollarSign},{label:'Monthly spend',icon:CreditCard},{label:'Budgets',icon:WalletCards},{label:'Ask',icon:Bot}]},
]
type Props={active:string;onSelect:(x:string)=>void;collapsed:boolean;mobileOpen:boolean;onClose:()=>void}
export default function Sidebar({active,onSelect,collapsed,mobileOpen,onClose}:Props){return <>
 {mobileOpen&&<button aria-label="Close navigation" className="sidebar-scrim" onClick={onClose}/>}
 <aside className={`sidebar ${collapsed?'sidebar-collapsed':''} ${mobileOpen?'sidebar-mobile-open':''}`}>
  <div className="brand-row"><div className="brand-mark"><Activity size={19}/></div>{!collapsed&&<span className="brand-name">Finora<span className="brand-dot">.</span></span>}<button className="icon-button sidebar-close" onClick={onClose} aria-label="Close navigation">×</button></div>
  {!collapsed&&<div className="sidebar-wallet"><div className="wallet-icon"><WalletCards size={15}/></div><div><small>Personal workspace</small><b>Private & local</b></div><span className="secure-dot"/></div>}
  <div className="nav-scroll">{nav.map(group=><section className="nav-section" key={group.title}>{!collapsed&&<div className="nav-caption">{group.title}</div>}{group.items.map(({label,icon:Icon})=><button key={label} title={collapsed?label:undefined} className={`nav-link ${active===label?'nav-link-active':''}`} onClick={()=>{onSelect(label);onClose()}}><Icon size={17} strokeWidth={1.8}/><span>{label}</span>{active===label&&!collapsed&&<ChevronRight className="nav-chevron" size={14}/>}</button>)}</section>)}</div>
  {!collapsed&&<div className="sidebar-privacy"><div className="privacy-icon"><Sparkles size={14}/></div><b>Your finances stay yours</b><p>Statements are processed in this browser and stay on this device.</p><span><span className="secure-dot"/> Local workspace</span></div>}
  <div className="sidebar-bottom"><div className="avatar-mini">FA</div>{!collapsed&&<div className="profile-copy"><b>Finance Analyzer</b><span>Personal account</span></div>}<Settings2 className="presence" size={14}/></div>
 </aside></>}
