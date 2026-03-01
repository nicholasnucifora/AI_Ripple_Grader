import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import Layout from '../components/Layout'
import { api } from '../api/client'

export default function AssignmentFormPage() {
  const { id: classId, aid: assignmentId } = useParams()
  const navigate = useNavigate()
  const editing = !!assignmentId

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [markingCriteria, setMarkingCriteria] = useState('')
  const [strictness, setStrictness] = useState('standard')
  const [loading, setLoading] = useState(editing)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!editing) return
    api.getAssignment(classId, assignmentId)
      .then((a) => {
        setTitle(a.title)
        setDescription(a.description ?? '')
        setMarkingCriteria(a.marking_criteria ?? '')
        setStrictness(a.strictness ?? 'standard')
      })
      .catch(() => setError('Failed to load assignment.'))
      .finally(() => setLoading(false))
  }, [classId, assignmentId, editing])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!title.trim()) return setError('Title is required.')
    setSaving(true)
    setError('')
    const body = {
      title: title.trim(),
      description: description.trim(),
      marking_criteria: markingCriteria.trim(),
      strictness,
    }
    try {
      let assignment
      if (editing) {
        assignment = await api.updateAssignment(classId, assignmentId, body)
      } else {
        assignment = await api.createAssignment(classId, body)
      }
      navigate(`/classes/${classId}/assignments/${assignment.id}`)
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  if (loading) return <Layout><p className="text-gray-500">Loading…</p></Layout>

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        {/* Breadcrumb */}
        <p className="text-sm text-gray-500 mb-1">
          <Link to="/" className="hover:underline">My Classes</Link>
          {' / '}
          <Link to={`/classes/${classId}`} className="hover:underline">Class</Link>
          {editing && (
            <>
              {' / '}
              <Link to={`/classes/${classId}/assignments/${assignmentId}`} className="hover:underline">Assignment</Link>
            </>
          )}
          {' /'}
        </p>

        <h1 className="text-2xl font-bold text-gray-900 mb-6">
          {editing ? 'Edit Assignment' : 'New Assignment'}
        </h1>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error && <p className="text-sm text-red-600">{error}</p>}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Marking Criteria</label>
            <textarea
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows={6}
              value={markingCriteria}
              onChange={(e) => setMarkingCriteria(e.target.value)}
              placeholder="Describe how submissions should be graded…"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Strictness</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={strictness}
              onChange={(e) => setStrictness(e.target.value)}
            >
              <option value="lenient">Lenient</option>
              <option value="standard">Standard</option>
              <option value="strict">Strict</option>
            </select>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving…' : editing ? 'Save Changes' : 'Create Assignment'}
            </button>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-5 py-2 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </Layout>
  )
}
