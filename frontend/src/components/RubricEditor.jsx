import { useMemo } from 'react'
import {
  useReactTable,
  getCoreRowModel,
} from '@tanstack/react-table'
import { validateRubric } from '../utils/rubricSchema'

// ---------------------------------------------------------------------------
// Inline editable field helpers
// ---------------------------------------------------------------------------

function InlineText({ value, onChange, readOnly, className = '', placeholder = '' }) {
  if (readOnly) return <span className={className}>{value}</span>
  return (
    <input
      className={`border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none bg-transparent ${className}`}
      value={value}
      placeholder={placeholder}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

function InlineNumber({ value, onChange, readOnly, className = '' }) {
  if (readOnly) return <span className={className}>{value}</span>
  return (
    <input
      type="number"
      className={`w-20 border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none bg-transparent ${className}`}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
    />
  )
}

function InlineTextarea({ value, onChange, readOnly, className = '' }) {
  if (readOnly) return <p className={`text-sm text-gray-600 ${className}`}>{value}</p>
  return (
    <textarea
      rows={2}
      className={`w-full border border-gray-200 rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 resize-none ${className}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

// ---------------------------------------------------------------------------
// LevelCard
// ---------------------------------------------------------------------------

function LevelCard({ level, onUpdate, onDelete, readOnly }) {
  function update(field, val) {
    onUpdate({ ...level, [field]: val })
  }

  return (
    <div className="flex-shrink-0 w-52 border border-gray-200 rounded-lg p-3 bg-white space-y-1">
      <div className="flex items-center justify-between">
        <InlineText
          value={level.title}
          onChange={(v) => update('title', v)}
          readOnly={readOnly}
          className="font-medium text-sm text-gray-800 w-32"
          placeholder="Level title"
        />
        {!readOnly && (
          <button
            type="button"
            onClick={onDelete}
            className="text-xs text-red-400 hover:text-red-600 ml-1"
            title="Remove level"
          >
            ✕
          </button>
        )}
      </div>
      <div className="flex items-center gap-1 text-xs text-gray-500">
        <span>Pts:</span>
        <InlineNumber
          value={level.points}
          onChange={(v) => update('points', v)}
          readOnly={readOnly}
          className="text-xs"
        />
      </div>
      <InlineTextarea
        value={level.description}
        onChange={(v) => update('description', v)}
        readOnly={readOnly}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// CriterionRow
// ---------------------------------------------------------------------------

function CriterionRow({ criterion, onUpdate, onDelete, readOnly }) {
  function updateLevel(levelId, updated) {
    onUpdate({
      ...criterion,
      levels: criterion.levels.map((l) => (l.id === levelId ? updated : l)),
    })
  }

  function deleteLevel(levelId) {
    onUpdate({ ...criterion, levels: criterion.levels.filter((l) => l.id !== levelId) })
  }

  function addLevel() {
    const newLevel = {
      id: crypto.randomUUID(),
      title: 'New Level',
      points: 0,
      description: '',
    }
    onUpdate({ ...criterion, levels: [...criterion.levels, newLevel] })
  }

  return (
    <div className="flex flex-row gap-3 border border-gray-200 rounded-xl p-4 bg-gray-50">
      {/* Criterion header (fixed width) */}
      <div className="flex-shrink-0 w-48 flex flex-col gap-2">
        <InlineText
          value={criterion.name}
          onChange={(v) => onUpdate({ ...criterion, name: v })}
          readOnly={readOnly}
          className="font-semibold text-sm text-gray-800 w-full"
          placeholder="Criterion name"
        />
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <InlineNumber
            value={criterion.weight_percentage}
            onChange={(v) => onUpdate({ ...criterion, weight_percentage: v })}
            readOnly={readOnly}
          />
          <span>%</span>
        </div>
        {!readOnly && (
          <button
            type="button"
            onClick={onDelete}
            className="text-xs text-red-500 hover:text-red-700 self-start"
          >
            Delete criterion
          </button>
        )}
      </div>

      {/* Level cards (horizontally scrollable) */}
      <div className="flex flex-row gap-2 overflow-x-auto pb-1 flex-1">
        {criterion.levels.map((level) => (
          <LevelCard
            key={level.id}
            level={level}
            onUpdate={(updated) => updateLevel(level.id, updated)}
            onDelete={() => deleteLevel(level.id)}
            readOnly={readOnly}
          />
        ))}
        {!readOnly && (
          <button
            type="button"
            onClick={addLevel}
            className="flex-shrink-0 w-36 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center text-sm text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors"
          >
            + Add Level
          </button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// RubricEditor
// ---------------------------------------------------------------------------

export default function RubricEditor({ rubric, onChange, readOnly = false }) {
  const { errors, warnings } = useMemo(
    () => (rubric ? validateRubric(rubric) : { errors: [], warnings: [] }),
    [rubric]
  )

  // TanStack Table — state management only, no rendering of <table>
  const columns = useMemo(() => [{ accessorKey: 'id', header: 'ID' }], [])
  const table = useReactTable({
    data: rubric?.criteria ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  if (!rubric) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm border-2 border-dashed border-gray-200 rounded-xl">
        No rubric yet — upload a document above or build one manually below.
      </div>
    )
  }

  function updateCriterion(criterionId, updated) {
    onChange({
      ...rubric,
      criteria: rubric.criteria.map((c) => (c.id === criterionId ? updated : c)),
    })
  }

  function deleteCriterion(criterionId) {
    onChange({ ...rubric, criteria: rubric.criteria.filter((c) => c.id !== criterionId) })
  }

  function addCriterion() {
    const newCriterion = {
      id: crypto.randomUUID(),
      name: 'New Criterion',
      weight_percentage: 0,
      levels: [
        { id: crypto.randomUUID(), title: 'Excellent', points: 10, description: '' },
        { id: crypto.randomUUID(), title: 'Pass', points: 5, description: '' },
        { id: crypto.randomUUID(), title: 'Fail', points: 0, description: '' },
      ],
    }
    onChange({ ...rubric, criteria: [...rubric.criteria, newCriterion] })
  }

  return (
    <div className="space-y-4">
      {/* Rubric title */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Rubric title</span>
        <InlineText
          value={rubric.title}
          onChange={(v) => onChange({ ...rubric, title: v })}
          readOnly={readOnly}
          className="text-lg font-bold text-gray-800"
          placeholder="Rubric title"
        />
      </div>

      {/* Validation warnings */}
      {warnings.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {warnings.map((w, i) => (
            <span
              key={i}
              className="text-xs bg-orange-100 text-orange-700 px-3 py-1 rounded-full"
            >
              ⚠ {w}
            </span>
          ))}
        </div>
      )}

      {/* Criteria rows — driven by TanStack Table row model */}
      <div className="space-y-3">
        {table.getRowModel().rows.map((row) => {
          const criterion = row.original
          return (
            <CriterionRow
              key={criterion.id}
              criterion={criterion}
              onUpdate={(updated) => updateCriterion(criterion.id, updated)}
              onDelete={() => deleteCriterion(criterion.id)}
              readOnly={readOnly}
            />
          )
        })}
      </div>

      {!readOnly && (
        <button
          type="button"
          onClick={addCriterion}
          className="w-full py-2 border-2 border-dashed border-gray-300 rounded-xl text-sm text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors"
        >
          + Add Criterion
        </button>
      )}
    </div>
  )
}
