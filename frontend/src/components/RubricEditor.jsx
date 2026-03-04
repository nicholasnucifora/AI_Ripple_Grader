import { useMemo, useState, useEffect, useRef, Fragment } from 'react'
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
      className={`w-16 border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none bg-transparent ${className}`}
      value={value}
      onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
    />
  )
}

function InlineTextarea({ value, onChange, readOnly, className = '' }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = 'auto'
      ref.current.style.height = ref.current.scrollHeight + 'px'
    }
  }, [value])

  if (readOnly) {
    return (
      <p className={`text-sm text-gray-600 leading-relaxed ${className}`}>
        {value || <span className="italic text-gray-300">—</span>}
      </p>
    )
  }
  return (
    <textarea
      ref={ref}
      rows={1}
      className={`w-full bg-transparent text-sm text-gray-700 focus:outline-none resize-none placeholder-gray-300 overflow-hidden ${className}`}
      value={value}
      placeholder="Describe this level…"
      onChange={(e) => onChange(e.target.value)}
    />
  )
}

// ---------------------------------------------------------------------------
// Group criteria by their sorted level-title signature
// ---------------------------------------------------------------------------

function getLevelSignature(criterion) {
  return [...criterion.levels]
    .sort((a, b) => b.points - a.points)
    .map((l) => l.title)
    .join('||')
}

function groupCriteria(criteria) {
  const groups = []
  const sigMap = new Map()
  for (const criterion of criteria) {
    const sig = getLevelSignature(criterion)
    if (sigMap.has(sig)) {
      groups[sigMap.get(sig)].criteria.push(criterion)
    } else {
      sigMap.set(sig, groups.length)
      const headerLevels = [...criterion.levels].sort((a, b) => b.points - a.points)
      groups.push({ sig, headerLevels, criteria: [criterion] })
    }
  }
  return groups
}

// ---------------------------------------------------------------------------
// RubricGroup — one CSS grid per set of criteria sharing the same level columns
// ---------------------------------------------------------------------------

function RubricGroup({ group, onUpdate, onDelete, readOnly, onAddRow, onAddColumn }) {
  const { headerLevels, criteria } = group
  const [hoveredId, setHoveredId] = useState(null)

  function updateDescription(criterion, levelId, val) {
    onUpdate({
      ...criterion,
      levels: criterion.levels.map((l) =>
        l.id === levelId ? { ...l, description: val } : l
      ),
    })
  }

  const colTemplate = `minmax(140px, 200px) repeat(${headerLevels.length}, 1fr)${!readOnly ? ' 2rem' : ''}`

  return (
    <div className="space-y-1">
      <div
        className="grid border border-gray-200 rounded-lg overflow-hidden"
        style={{ gridTemplateColumns: colTemplate }}
      >
        {/* Header row */}
        <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Criterion
        </div>
        {headerLevels.map((level) => (
          <div key={level.id} className="px-4 py-2 bg-gray-50 border-b border-l border-gray-200">
            <div className="text-sm font-semibold text-gray-800">{level.title}</div>
            <div className="text-xs text-gray-400">{level.points} pts</div>
          </div>
        ))}
        {!readOnly && (
          <div className="bg-gray-50 border-b border-l border-gray-200 flex items-center justify-center">
            <button
              type="button"
              onClick={onAddColumn}
              title="Add column"
              className="w-full h-full text-gray-400 hover:text-blue-500 hover:bg-blue-50 transition-colors text-base font-medium"
            >
              +
            </button>
          </div>
        )}

        {/* Criterion rows */}
        {criteria.map((criterion, rowIdx) => {
          const isHovered = hoveredId === criterion.id
          const isLast = rowIdx === criteria.length - 1
          const sortedLevels = [...criterion.levels].sort((a, b) => b.points - a.points)
          const borderB = isLast ? '' : 'border-b border-gray-200'
          const rowBg = isHovered ? 'bg-blue-50' : ''

          return (
            <Fragment key={criterion.id}>
              {/* Criterion name + weight cell */}
              <div
                className={`relative px-4 py-3 flex flex-col gap-1 ${borderB} ${rowBg} transition-colors`}
                onMouseEnter={() => setHoveredId(criterion.id)}
                onMouseLeave={() => setHoveredId(null)}
              >
                <InlineText
                  value={criterion.name}
                  onChange={(v) => onUpdate({ ...criterion, name: v })}
                  readOnly={readOnly}
                  className="font-semibold text-sm text-gray-800 w-full"
                  placeholder="Criterion name"
                />
                <div className="flex items-center gap-1 text-xs text-gray-400">
                  <InlineNumber
                    value={criterion.weight_percentage}
                    onChange={(v) => onUpdate({ ...criterion, weight_percentage: v })}
                    readOnly={readOnly}
                    className="text-xs"
                  />
                  <span>%</span>
                </div>
                {!readOnly && (
                  <button
                    type="button"
                    onClick={() => onDelete(criterion.id)}
                    className={`absolute top-2 right-2 text-gray-400 hover:text-red-500 text-xs transition-opacity ${isHovered ? 'opacity-100' : 'opacity-0'}`}
                    title="Remove criterion"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Level description cells */}
              {sortedLevels.map((level) => (
                <div
                  key={level.id}
                  className={`px-4 py-3 border-l border-gray-200 ${borderB} ${rowBg} transition-colors`}
                  onMouseEnter={() => setHoveredId(criterion.id)}
                  onMouseLeave={() => setHoveredId(null)}
                >
                  <InlineTextarea
                    value={level.description}
                    onChange={(v) => updateDescription(criterion, level.id, v)}
                    readOnly={readOnly}
                  />
                </div>
              ))}

              {/* Spacer cell for the + column */}
              {!readOnly && <div className={`border-l border-gray-200 ${borderB}`} />}
            </Fragment>
          )
        })}
      </div>

      {/* Add row button — below this group's table */}
      {!readOnly && (
        <button
          type="button"
          onClick={onAddRow}
          className="w-full py-1.5 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-400 hover:border-blue-400 hover:text-blue-500 transition-colors"
        >
          +
        </button>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// RubricEditor
// ---------------------------------------------------------------------------

export default function RubricEditor({ rubric, onChange, readOnly = false }) {
  const { warnings } = useMemo(
    () => (rubric ? validateRubric(rubric) : { errors: [], warnings: [] }),
    [rubric]
  )

  // Group criteria by their level signature — different level sets → separate grids
  const groups = useMemo(() => groupCriteria(rubric?.criteria ?? []), [rubric])

  if (!rubric) {
    return (
      <div className="text-center py-8 text-gray-400 text-sm border-2 border-dashed border-gray-200 rounded-xl">
        No rubric yet — upload a document above or build one manually below.
      </div>
    )
  }

  function updateCriterion(updated) {
    onChange({
      ...rubric,
      criteria: rubric.criteria.map((c) => (c.id === updated.id ? updated : c)),
    })
  }

  function deleteCriterion(criterionId) {
    onChange({ ...rubric, criteria: rubric.criteria.filter((c) => c.id !== criterionId) })
  }

  function addCriterionToGroup(group) {
    const newCriterion = {
      id: crypto.randomUUID(),
      name: 'New Criterion',
      weight_percentage: 0,
      levels: group.headerLevels.map((l) => ({
        id: crypto.randomUUID(),
        title: l.title,
        points: l.points,
        description: '',
      })),
    }
    onChange({ ...rubric, criteria: [...rubric.criteria, newCriterion] })
  }

  function addColumnToGroup(group) {
    const criteriaIds = new Set(group.criteria.map((c) => c.id))
    onChange({
      ...rubric,
      criteria: rubric.criteria.map((c) => {
        if (!criteriaIds.has(c.id)) return c
        return {
          ...c,
          levels: [
            ...c.levels,
            { id: crypto.randomUUID(), title: 'New Level', points: 0, description: '' },
          ],
        }
      }),
    })
  }

  return (
    <div className="space-y-3">
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
            <span key={i} className="text-xs bg-orange-100 text-orange-700 px-3 py-1 rounded-full">
              ⚠ {w}
            </span>
          ))}
        </div>
      )}

      {/* One grid per unique level-column set */}
      <div className="space-y-5">
        {groups.map((group) => (
          <RubricGroup
            key={group.sig}
            group={group}
            onUpdate={updateCriterion}
            onDelete={deleteCriterion}
            readOnly={readOnly}
            onAddRow={() => addCriterionToGroup(group)}
            onAddColumn={() => addColumnToGroup(group)}
          />
        ))}
      </div>
    </div>
  )
}
