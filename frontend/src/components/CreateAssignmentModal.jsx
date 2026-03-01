import { useState } from 'react'
import Modal from './Modal'
import { api } from '../api/client'

export default function CreateAssignmentModal({ classId, initial, onClose, onSaved }) {
  const editing = !!initial
  const [title, setTitle] = useState(initial?.title ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [markingCriteria, setMarkingCriteria] = useState(initial?.marking_criteria ?? '')
  const [strictness, setStrictness] = useState(initial?.strictness ?? 'standard')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!title.trim()) return setError('Title is required')
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
        assignment = await api.updateAssignment(classId, initial.id, body)
      } else {
        assignment = await api.createAssignment(classId, body)
      }
      onSaved(assignment)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal title={editing ? 'Edit Assignment' : 'New Assignment'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
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
            rows={5}
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
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : editing ? 'Save Changes' : 'Create Assignment'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
