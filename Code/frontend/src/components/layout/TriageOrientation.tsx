/**
 * TriageOrientation
 *
 * Shown once, after calibration and before the first triage case.
 * Explains the clinical task and the decision rules to non-medical users.
 */

interface Props {
  onReady: () => void;
}

const LEVELS: { label: string; color: string; bg: string; criteria: string[] }[] = [
  {
    label: 'High',
    color: '#b91c1c',
    bg: '#fef2f2',
    criteria: [
      'Life-threatening condition requiring immediate intervention',
      'Airway compromise, uncontrolled haemorrhage, or altered consciousness',
      'Vital signs severely outside normal range (e.g. SBP < 90 mmHg, SpO₂ < 90%)',
    ],
  },
  {
    label: 'Moderate',
    color: '#b45309',
    bg: '#fffbeb',
    criteria: [
      'Potentially serious condition — could deteriorate without treatment',
      'Significant pain (7–10/10) or distress but currently stable',
      'Abnormal but not critical vital signs',
    ],
  },
  {
    label: 'Low',
    color: '#15803d',
    bg: '#f0fdf4',
    criteria: [
      'Non-urgent complaint — unlikely to deteriorate in the next few hours',
      'Mild symptoms, mild pain (1–6/10), normal vital signs',
      'Can safely wait for assessment',
    ],
  },
  {
    label: 'Stable',
    color: '#1d4ed8',
    bg: '#eff6ff',
    criteria: [
      'Chronic or administrative presentation — no acute clinical concern',
      'Follow-up, prescription refill, or minor injury with no functional impairment',
      'All vital signs within normal limits',
    ],
  },
];

export function TriageOrientation({ onReady }: Props) {
  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.heading}>Clinical Triage Task</h1>
        <p style={styles.intro}>
          You will be shown a series of patient presentations, each containing a chief
          complaint, vital signs, and clinical findings. Your job is to assign each
          patient to the correct triage level, as a clinician would in an emergency
          department.
        </p>
        <p style={styles.intro}>
          You do not need a medical background — read each case carefully and apply
          the rules below. Respond as quickly and accurately as you can.
        </p>

        <h2 style={styles.sectionHeading}>Decision Rules</h2>
        <div style={styles.levels}>
          {LEVELS.map((level) => (
            <div key={level.label} style={{ ...styles.levelCard, background: level.bg, borderColor: level.color }}>
              <div style={{ ...styles.levelBadge, background: level.color }}>
                {level.label}
              </div>
              <ul style={styles.criteriaList}>
                {level.criteria.map((c, i) => (
                  <li key={i} style={styles.criteriaItem}>{c}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <h2 style={styles.sectionHeading}>Key Reminders</h2>
        <ul style={styles.reminderList}>
          <li>Read <strong>all</strong> the information before deciding — don't anchor on the first detail.</li>
          <li>Vital signs take priority over the patient's stated complaint.</li>
          <li>Age and appearance alone are not reliable indicators of severity.</li>
          <li>When in doubt between two levels, choose the more urgent one.</li>
        </ul>

        <button style={styles.btn} onClick={onReady}>
          I understand — begin cases
        </button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100%',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    padding: '40px 24px',
    background: '#f9fafb',
  },
  card: {
    maxWidth: 680,
    width: '100%',
    background: '#fff',
    borderRadius: 10,
    padding: '40px 44px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
  },
  heading: {
    fontSize: 24,
    fontWeight: 700,
    color: '#111827',
    marginTop: 0,
    marginBottom: 16,
  },
  intro: {
    fontSize: 15,
    color: '#374151',
    lineHeight: 1.7,
    marginBottom: 12,
  },
  sectionHeading: {
    fontSize: 14,
    fontWeight: 700,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.6,
    color: '#6b7280',
    marginTop: 32,
    marginBottom: 14,
  },
  levels: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 12,
  },
  levelCard: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 16,
    padding: '14px 16px',
    borderRadius: 8,
    border: '1px solid',
  },
  levelBadge: {
    color: '#fff',
    fontWeight: 700,
    fontSize: 13,
    borderRadius: 4,
    padding: '3px 10px',
    whiteSpace: 'nowrap' as const,
    flexShrink: 0,
    marginTop: 1,
  },
  criteriaList: {
    margin: 0,
    paddingLeft: 18,
    fontSize: 14,
    color: '#374151',
    lineHeight: 1.65,
  },
  criteriaItem: {
    marginBottom: 3,
  },
  reminderList: {
    fontSize: 14,
    color: '#374151',
    lineHeight: 1.75,
    paddingLeft: 20,
    marginTop: 0,
  },
  btn: {
    display: 'block',
    marginTop: 36,
    width: '100%',
    padding: '13px 0',
    background: '#1d4ed8',
    color: '#fff',
    border: 'none',
    borderRadius: 7,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
  },
};
