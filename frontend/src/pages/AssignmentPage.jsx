import { useEffect, useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import SubmitAssignmentModal from '../components/SubmitAssignmentModal'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api/client'

export default function AssignmentPage() {
  const { id: classId, aid: assignmentId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [assignment, setAssignment] = useState(null)
  const [submissions, setSubmissions] = useState([])
  const [loadingAssignment, setLoadingAssignment] = useState(true)
  const [loadingSubmissions, setLoadingSubmissions] = useState(true)
  const [showSubmit, setShowSubmit] = useState(false)
  const [myMemberRole, setMyMemberRole] = useState(null)
  const [rippleStats, setRippleStats] = useState(null)
  const [rippleImporting, setRippleImporting] = useState(false)
  const [rippleMessage, setRippleMessage] = useState(null) // { ok: bool, text: str }
  const [gradeJob, setGradeJob] = useState(null)
  const [gradeResults, setGradeResults] = useState(null)
  const [expandedResult, setExpandedResult] = useState(null)

  useEffect(() => {
    // Fetch class to determine role
    api.getClass(classId).then((cls) => {
      const m = cls.members.find((mem) => mem.user_id === user?.user_id)
      const role = m?.role ?? 'student'
      setMyMemberRole(role)
      if (role === 'teacher') {
        api.getRippleStats(classId, assignmentId).then(setRippleStats).catch(() => {})
        api.getGradeStatus(classId, assignmentId).then((job) => setGradeJob(job ?? null)).catch(() => {})
      }
    })

    api.getAssignment(classId, assignmentId)
      .then(setAssignment)
      .finally(() => setLoadingAssignment(false))

    api.listSubmissions(classId, assignmentId)
      .then(setSubmissions)
      .finally(() => setLoadingSubmissions(false))
  }, [classId, assignmentId, user])

  async function handleRippleCsvUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    e.target.value = ''
    setRippleImporting(true)
    setRippleMessage(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const result = await api.importRippleCsv(classId, assignmentId, formData)
      const label = result.type === 'resource' ? 'Resource' : 'Moderation'
      setRippleMessage({ ok: true, text: `${label} export — ${result.imported} records imported` })
      api.getRippleStats(classId, assignmentId).then(setRippleStats).catch(() => {})
    } catch (err) {
      setRippleMessage({ ok: false, text: err.message })
    } finally {
      setRippleImporting(false)
    }
  }

  // Poll for grading status when job is active
  useEffect(() => {
    if (!gradeJob) return
    const active = gradeJob.status === 'queued' || gradeJob.status === 'running'
    if (!active) {
      if (gradeJob.status === 'complete') {
        api.getGradeResults(classId, assignmentId).then(setGradeResults).catch(() => {})
      }
      return
    }
    const interval = setInterval(() => {
      api.getGradeStatus(classId, assignmentId)
        .then((job) => {
          setGradeJob(job ?? null)
          if (job && job.status === 'complete') {
            api.getGradeResults(classId, assignmentId).then(setGradeResults).catch(() => {})
          }
        })
        .catch(() => {})
    }, 3000)
    return () => clearInterval(interval)
  }, [gradeJob?.status, classId, assignmentId])

  async function handleStartGrading() {
    try {
      const job = await api.startGrading(classId, assignmentId)
      setGradeJob(job)
      setGradeResults(null)
    } catch (err) {
      alert(err.message)
    }
  }

  async function handleCancelGrading() {
    try {
      const job = await api.cancelGrading(classId, assignmentId)
      setGradeJob(job)
    } catch (err) {
      alert(err.message)
    }
  }

  async function handleDeleteGrading() {
    if (!confirm('Delete all AI grading results for this assignment?')) return
    try {
      await api.deleteGrading(classId, assignmentId)
      setGradeJob(null)
      setGradeResults(null)
    } catch (err) {
      alert(err.message)
    }
  }

  if (loadingAssignment) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!assignment) return <Layout><p className="text-red-600">Assignment not found.</p></Layout>

  const isTeacher = myMemberRole === 'teacher'
  const mySubmission = submissions.find((s) => s.student_user_id === user?.user_id)

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
              onClick={() => navigate(`/classes/${classId}/assignments/${assignmentId}/edit`)}
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

        {/* RiPPLE Data — teacher only */}
        {isTeacher && (
          <section className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-gray-800">RiPPLE Data</h2>
                {rippleStats && (
                  <p className="text-sm text-gray-500 mt-0.5">
                    Resources: {rippleStats.resources} rows · Moderations: {rippleStats.moderations} rows
                  </p>
                )}
                {rippleMessage && (
                  <p className={`text-sm mt-1 ${rippleMessage.ok ? 'text-green-600' : 'text-red-600'}`}>
                    {rippleMessage.ok ? '✓ ' : ''}{rippleMessage.text}
                  </p>
                )}
              </div>
              <label className={`px-3 py-1.5 text-sm rounded-lg cursor-pointer shrink-0 ${
                rippleImporting
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              }`}>
                {rippleImporting ? 'Importing…' : 'Upload CSV'}
                <input
                  type="file"
                  accept=".csv"
                  className="hidden"
                  disabled={rippleImporting}
                  onChange={handleRippleCsvUpload}
                />
              </label>
            </div>
          </section>
        )}

        {/* AI Grading — teacher only */}
        {isTeacher && (
          <AiGradingSection
            rippleStats={rippleStats}
            assignment={assignment}
            gradeJob={gradeJob}
            gradeResults={gradeResults}
            expandedResult={expandedResult}
            setExpandedResult={setExpandedResult}
            onStart={handleStartGrading}
            onCancel={handleCancelGrading}
            onDelete={handleDeleteGrading}
          />
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

function AiGradingSection({
  rippleStats,
  assignment,
  gradeJob,
  gradeResults,
  expandedResult,
  setExpandedResult,
  onStart,
  onCancel,
  onDelete,
}) {
  const hasResources = rippleStats && rippleStats.resources > 0
  const hasRubric = !!assignment.rubric_id || assignment.has_rubric
  // Derive readiness from rubric: if assignment doesn't carry a flag, we rely on backend
  // guarding. We show the button; the backend will 400 if rubric is missing.
  const canStart = hasResources

  const status = gradeJob?.status

  function missingTooltip() {
    if (!hasResources) return 'Upload a RiPPLE resource CSV first'
    return ''
  }

  const progressPct =
    gradeJob && gradeJob.total > 0
      ? Math.round((gradeJob.graded / gradeJob.total) * 100)
      : 0

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5 mb-6">
      <h2 className="font-semibold text-gray-800 mb-3">AI Grading</h2>

      {/* No job yet */}
      {!gradeJob && (
        <div className="flex items-center gap-3">
          <button
            onClick={onStart}
            disabled={!canStart}
            title={missingTooltip()}
            className={`px-3 py-1.5 text-sm rounded-lg ${
              canStart
                ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            Start Grading
          </button>
          {!canStart && (
            <span className="text-sm text-gray-400">{missingTooltip()}</span>
          )}
        </div>
      )}

      {/* Queued */}
      {status === 'queued' && (
        <p className="text-sm text-gray-500">Queued — worker will pick this up shortly…</p>
      )}

      {/* Running */}
      {status === 'running' && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-700">
              Grading resources… {gradeJob.graded} / {gradeJob.total}
            </span>
            <button
              onClick={onCancel}
              className="px-3 py-1 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-indigo-500 h-2 rounded-full transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Complete */}
      {status === 'complete' && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <span className="text-sm text-green-700 font-medium">
              {gradeJob.graded} graded{gradeJob.errors > 0 ? ` · ${gradeJob.errors} errors` : ''}
            </span>
            <button
              onClick={onDelete}
              className="px-3 py-1.5 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
            >
              Delete AI Grading
            </button>
          </div>
          {gradeResults && gradeResults.length > 0 && (
            <GradeResultsTable
              results={gradeResults}
              expandedResult={expandedResult}
              setExpandedResult={setExpandedResult}
            />
          )}
        </div>
      )}

      {/* Cancelled / Error */}
      {(status === 'cancelled' || status === 'error') && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500 capitalize">{status}</span>
          <button
            onClick={onDelete}
            className="px-3 py-1.5 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
          >
            Delete AI Grading
          </button>
        </div>
      )}
    </section>
  )
}

function GradeResultsTable({ results, expandedResult, setExpandedResult }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border border-gray-200 rounded-xl overflow-hidden">
        <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
          <tr>
            <th className="px-4 py-3 text-left">Resource</th>
            <th className="px-4 py-3 text-left">Author</th>
            <th className="px-4 py-3 text-left">Score</th>
            <th className="px-4 py-3 text-left">Feedback</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {results.map((r) => {
            const score = r.criterion_grades
              ? r.criterion_grades.reduce((s, g) => s + (g.points_awarded || 0), 0)
              : 0
            const maxScore = r.criterion_grades
              ? r.criterion_grades.reduce((s, g) => {
                  // best-effort max; we don't have rubric here so just show total
                  return s + (g.points_awarded || 0)
                }, 0)
              : 0
            const isExpanded = expandedResult === r.id
            return [
              <tr
                key={r.id}
                className="bg-white hover:bg-gray-50 cursor-pointer"
                onClick={() => setExpandedResult(isExpanded ? null : r.id)}
              >
                <td className="px-4 py-3 font-mono text-gray-700">{r.resource_id}</td>
                <td className="px-4 py-3 text-gray-600">{r.primary_author_name || '—'}</td>
                <td className="px-4 py-3 text-gray-800 font-medium">
                  {r.status === 'error' ? (
                    <span className="text-red-500">Error</span>
                  ) : (
                    score.toFixed(1)
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500 truncate max-w-xs">
                  {r.status === 'error' ? r.error_message : r.overall_feedback}
                </td>
              </tr>,
              isExpanded && r.criterion_grades && r.criterion_grades.length > 0 && (
                <tr key={`${r.id}-detail`} className="bg-indigo-50">
                  <td colSpan={4} className="px-4 py-3">
                    <div className="text-xs font-semibold text-gray-600 mb-2">Criterion Breakdown</div>
                    <div className="space-y-2">
                      {r.criterion_grades.map((g, i) => (
                        <div key={i} className="flex flex-col gap-0.5">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-700">{g.criterion_name}</span>
                            <span className="text-indigo-700 font-semibold">{g.level_title} ({g.points_awarded} pts)</span>
                          </div>
                          <p className="text-gray-500 pl-1">{g.feedback}</p>
                        </div>
                      ))}
                    </div>
                    {r.overall_feedback && (
                      <div className="mt-3 pt-3 border-t border-indigo-200">
                        <div className="text-xs font-semibold text-gray-600 mb-1">Overall Feedback</div>
                        <p className="text-gray-700 text-sm">{r.overall_feedback}</p>
                      </div>
                    )}
                  </td>
                </tr>
              ),
            ]
          })}
        </tbody>
      </table>
    </div>
  )
}
