import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import {
  Activity,
  ArrowUpRight,
  Bot,
  ClipboardCheck,
  FileClock,
  FileText,
  LayoutDashboard,
  SquareStack,
  Wrench,
} from 'lucide-react';
import { useLandingReducedMotion } from './LandingMotion';

const MotionLink = motion.create(Link);
const destinations = [
  {
    name: 'Dashboard',
    description: 'Your health overview and the next useful action.',
    path: '/dashboard',
    tone: 'blue',
    icon: LayoutDashboard,
  },
  {
    name: 'Applications',
    description: 'Explore the designated local sample.',
    path: '/applications',
    tone: 'green',
    icon: SquareStack,
  },
  {
    name: 'AI Agents',
    description: 'Understand the six roles behind the workflow.',
    path: '/agents',
    tone: 'violet',
    icon: Bot,
  },
  {
    name: 'Incidents',
    description: 'Find an issue and follow its evidence.',
    path: '/incidents',
    tone: 'rose',
    icon: Activity,
  },
  {
    name: 'Repair & Testing',
    description: 'Compare proposals and inspect test results.',
    path: '/repair-testing',
    tone: 'amber',
    icon: Wrench,
  },
  {
    name: 'Approval & Recovery',
    description: 'Make a decision. Apply separately.',
    path: '/approval-recovery',
    tone: 'teal',
    icon: ClipboardCheck,
  },
  {
    name: 'Incident History',
    description: 'Revisit decisions and recovery outcomes.',
    path: '/history',
    tone: 'indigo',
    icon: FileClock,
  },
  {
    name: 'Reports',
    description: 'See a recorded outcome and its limitations.',
    path: '/incidents/inc_005?tab=report',
    tone: 'plum',
    icon: FileText,
  },
] as const;

export function WorkspaceExplorer() {
  const reduce = useLandingReducedMotion();
  return (
    <div className="workspace-explorer">
      {destinations.map(({ name, description, path, tone, icon: Icon }, index) => (
        <motion.div
          className="workspace-tile-slot"
          key={name}
          initial={reduce ? false : { opacity: 0, x: index % 2 ? 18 : -18 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true, amount: 0.2 }}
          transition={{ duration: 0.5, delay: (index % 2) * 0.07, ease: [0.22, 1, 0.36, 1] }}
        >
          <MotionLink
            to={path}
            className={`workspace-tile workspace-tone-${tone}`}
            whileHover={reduce ? undefined : { x: 6, y: -2 }}
            whileFocus={reduce ? undefined : { x: 6, y: -2 }}
            whileTap={reduce ? undefined : { x: 2, y: 0, scale: 0.99 }}
            transition={{ type: 'spring', stiffness: 240, damping: 25 }}
          >
            <span className="workspace-icon-window" aria-hidden="true">
              <span className="workspace-icon-reel">
                <span>
                  <Icon size={23} />
                </span>
                <span>
                  <Icon size={23} />
                </span>
              </span>
            </span>
            <div className="workspace-tile-copy">
              <h3>{name}</h3>
              <p>{description}</p>
            </div>
            <span className="workspace-tile-arrow" aria-hidden="true">
              <ArrowUpRight size={18} />
            </span>
          </MotionLink>
        </motion.div>
      ))}
    </div>
  );
}
