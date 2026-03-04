import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import Layout from '../components/Layout'
import RubricIngestUploader from '../components/RubricIngestUploader'
import RubricEditor from '../components/RubricEditor'
import { api } from '../api/client'

export default function AssignmentFormPage() {
  const { id: classId } = useParams()
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [strictness, setStrictness] = useState('standard')
  const [rubric, setRubric] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!title.trim()) return setError('Title is required.')
    setSaving(true)
    setError('')
    try {
      const assignment = await api.createAssignment(classId, {
        title: title.trim(),
        description: description.trim(),
        marking_criteria: '',
        strictness,
      })
      if (rubric) {
        await api.saveRubric(classId, assignment.id, { rubric })
      }
      navigate(`/classes/${classId}/assignments/${assignment.id}`)
    } catch (err) {
      setError(err.message)
      setSaving(false)
    }
  }

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        {/* Breadcrumb */}
        <p className="text-sm text-gray-500 mb-1">
          <Link to="/" className="hover:underline">My Classes</Link>
          {' / '}
          <Link to={`/classes/${classId}`} className="hover:underline">Class</Link>
          {' /'}
        </p>

        <h1 className="text-2xl font-bold text-gray-900 mb-6">New Assignment</h1>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && <p className="text-sm text-red-600">{error}</p>}

          {/* Form fields — centered narrow column */}
          <div className="max-w-xl mx-auto space-y-6">
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
          </div>

          {/* Rubric section — full width of outer container */}
          <div className="border-t border-gray-200 pt-6 space-y-4">
            <h2 className="text-base font-semibold text-gray-800">Rubric</h2>
            <RubricIngestUploader onRubricExtracted={setRubric} />
            <RubricEditor rubric={rubric} onChange={setRubric} />
          </div>

          <div className="max-w-xl mx-auto flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Create Assignment'}
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
