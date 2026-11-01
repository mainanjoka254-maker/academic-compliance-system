import { useEffect, useState } from 'react'
import api from '@/services/api'
export default function Institutions(){ const [list,setList]=useState<any[]>([]); useEffect(()=>{api.get('/institutions').then(r=>setList(r.data)).catch(()=>{})},[]); return <div className="p-8 max-w-4xl mx-auto"><h1 className="text-3xl font-bold mb-4">Supported Institutions</h1><ul className="space-y-2">{list.map(i=><li key={i.id} className="bg-gray-50 p-3 rounded">{i.name} ({i.code})</li>)}</ul></div> }
