import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import Layout from '../components/Layout'
import CreateAssignmentModal from '../components/CreateAssignmentModal'
import SubmitAssignmentModal from '../components/SubmitAssignmentModal'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api/client'

export default function AssignmentPage() {
  const { id: classId, aid: assignmentId } = useParams()
  const { user } = useAuth()
  const [assignment, setAssignment] = useState(null)
  const [submissions, setSubmissions] = useState([])
  const [loadingAssignment, setLoadingAssignment] = useState(true)
  const [loadingSubmissions, setLoadingSubmissions] = useState(true)
  const [showEdit, setShowEdit] = useState(false)
  const [showSubmit, setShowSubmit] = useState(false)
  const [myMemberRole, setMyMemberRole] = useState(null)

  useEffect(() => {
    // Fetch class to determine role
    api.getClass(classId).then((cls) => {
      const m = cls.members.find((mem) => mem.user_id === user?.user_id)
      setMyMemberRole(m?.role ?? 'student')
    })

    api.getAssignment(classId, assignmentId)
      .then(setAssignment)
      .finally(() => setLoadingAssignment(false))

    api.listSubmissions(classId, assignmentId)
      .then(setSubmissions)
      .finally(() => setLoadingSubmissions(false))
  }, [classId, assignmentId, user])

  if (loadingAssignment) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!assignment) return <Layout><p className="text-red-600">Assignment not found.</p></Layout>

  const isTeacher = myMemberRole === 'teacher'
  const mySubmission = submissions.find((s) => s.student_user_id === user?.user_id)

  function handleAssignmentSaved(updated) {
    setAssignment(updated)
    setShowEdit(false)
  }

  function handleSubmitted(submission) {
    setSubmissions((prev) => [...prev, submission])
    setShowSubmit(false)
  }

  const strictnessColors = {
    lenient: 'bg-green-100 text-green-700',
    standard: 'bg-yellow-100 text-yellow-700',
    strict: 'bg-red-100 text-red-700',
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto">
        {/* Breadcrumb */}
        <p className="text-sm text-gray-500 mb-1">
          <Link to="/" className="hover:underline">My Classes</Link>
          {' / '}
          <Link to={`/classes/${classId}`} className="hover:underline">Class</Link>
          {' /'}
        </p>

        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900">{assignment.title}</h1>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                strictnessColors[assignment.strictness] ?? 'bg-gray-100 text-gray-600'
              }`}>
                {assignment.strictness}
              </span>
            </div>
            {assignment.description && (
              <p className="text-gray-600 mt-1">{assignment.description}</p>
            )}
          </div>
          {isTeacher && (
            <button
              onClick={() => setShowEdit(true)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 shrink-0"
            >
              Edit
            </button>
          )}
        </div>

        {/* Marking criteria */}
        {assignment.marking_criteria && (
          <section className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
            <h2 className="font-semibold text-gray-800 mb-2">Marking Criteria</h2>
            <p className="text-sm text-gray-700 whitespace-pre-wrap">{assignment.marking_criteria}</p>
          </section>
        )}

        {/* Submissions section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-800">
              {isTeacher ? `Submissions (${submissions.length})` : 'My Submission'}
            </h2>
            {!isTeacher && !mySubmission && (
              <button
                onClick={() => setShowSubmit(true)}
                className="px-3 py-1.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700"
              >
                Submit
              </button>
            )}
          </div>

          {loadingSubmissions ? (
            <p className="text-sm text-gray-500">Loading submissions…</p>
          ) : isTeacher ? (
            <TeacherSubmissionsTable submissions={submissions} />
          ) : mySubmission ? (
            <StudentSubmissionView submission={mySubmission} />
          ) : (
            <p className="text-sm text-gray-500">You haven't submitted yet.</p>
          )}
        </section>
      </div>

      {showEdit && (
        <CreateAssignmentModal
          classId={classId}
          initial={assignment}
          onClose={() => setShowEdit(false)}
          onSaved={handleAssignmentSaved}
        />
      )}
      {showSubmit && (
        <SubmitAssignmentModal
          classId={classId}
          assignmentId={assignmentId}
          onClose={() => setShowSubmit(false)}
          onSubmitted={handleSubmitted}
        />
      )}
    </Layout>
  )
}

function TeacherSubmissionsTable({ submissions }) {
  if (submissions.length === 0) {
    return <p className="text-sm text-gray-500">No submissions yet.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border border-gray-200 rounded-xl overflow-hidden">
        <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
          <tr>
            <th className="px-4 py-3 text-left">Student</th>
            <th className="px-4 py-3 text-left">Submitted</th>
            <th className="px-4 py-3 text-left">Preview</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {submissions.map((s) => (
            <tr key={s.id} className="bg-white hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-gray-800">{s.student_user_id}</td>
              <td className="px-4 py-3 text-gray-500">
                {new Date(s.submitted_at).toLocaleString()}
              </td>
              <td className="px-4 py-3 text-gray-600 truncate max-w-xs">{s.content}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StudentSubmissionView({ submission }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <p className="text-xs text-gray-500 mb-3">
        Submitted {new Date(submission.submitted_at).toLocaleString()}
      </p>
      <p className="text-sm text-gray-700 whitespace-pre-wrap">{submission.content}</p>
    </div>
  )
}
