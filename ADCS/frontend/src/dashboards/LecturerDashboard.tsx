import { useEffect, useState } from 'react'
import api from '@/services/api'
import AcademicDocumentsPanel from '@/components/AcademicDocumentsPanel'

type Course = { id: number; code: string; name: string }

export default function LecturerDashboard() {
  const [courses, setCourses] = useState<Course[]>([])
  const [students, setStudents] = useState<any[]>([])
  useEffect(() => {
    (async () => {
      try {
        const c = await api.get('/courses'); setCourses(c.data)
        const s = await api.get('/students'); setStudents(s.data)
      } catch {}
    })()
  }, [])
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-navy-900">Lecturer Dashboard</h1>
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">Assigned Courses</p><p className="text-3xl font-bold">{courses.length}</p></div>
        <div className="bg-white p-4 rounded-xl shadow"><p className="text-gray-500 text-sm">Students</p><p className="text-3xl font-bold">{students.length}</p></div>
      </div>
      <div className="bg-white p-4 rounded-xl shadow">
        <h2 className="font-semibold mb-2">Courses</h2>
        {courses.map((c:any)=><div key={c.id} className="border-b py-2">{c.code} - {c.name}</div>)}
      </div>
      <AcademicDocumentsPanel mode="lecturer" courses={courses} />
    </div>
  )
}
