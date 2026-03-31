import React from 'react';
import type { ReactNode } from 'react';
import { C4DiagramProvider } from '@site/src/components/C4Diagram';

/**
 * Docusaurus Root theme component.
 *
 * Wraps the entire site with C4DiagramProvider so that all <C4Diagram>
 * components in docs share one loaded module — no `module` prop needed
 * on individual diagrams.
 *
 * Generate the module with:
 *   npx likec4 gen react -o src/generated/likec4.mjs .
 */
export default function Root({ children }: { children: ReactNode }) {
  return (
    <C4DiagramProvider loader={() => import('@site/src/generated/likec4')}>
      {children}
    </C4DiagramProvider>
  );
}
