import { useRef } from 'react';
import { useInView } from 'motion/react';
import { team } from '../content/product';
import { agentIcons } from './workflow';
import { FeatureCard } from './FeatureCard';
import { useLandingReducedMotion } from './LandingMotion';

export function AgentTeam() {
  const reduce = useLandingReducedMotion();
  const container = useRef<HTMLDivElement>(null);
  const visible = useInView(container, { amount: 'some' });
  return (
    <div ref={container} className="agent-team-experience">
      <p className="agent-team-caption">Six roles. A shared purpose.</p>
      <div className="public-team" data-flow-running={!reduce && visible}>
        {team.map(([type, name, description, technical], index) => {
          const Icon = agentIcons[type];
          return (
            <FeatureCard
              key={type}
              index={index}
              className={`public-agent agent-${type}`}
              decoration={<span className="agent-color-flow" aria-hidden="true" />}
            >
              <div className="agent-card-heading">
                <span className="agent-icon">
                  <Icon size={24} aria-hidden />
                </span>
                <small>0{index + 1}</small>
              </div>
              <h3>{name}</h3>
              <p>{description}</p>
              <details>
                <summary>Behind the scenes</summary>
                <p>{technical}</p>
              </details>
            </FeatureCard>
          );
        })}
      </div>
    </div>
  );
}
