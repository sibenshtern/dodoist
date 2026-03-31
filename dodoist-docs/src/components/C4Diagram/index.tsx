import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import BrowserOnly from '@docusaurus/BrowserOnly';
import styles from './styles.module.css';

// ─── Types ───────────────────────────────────────────────────────────────────

/**
 * Shape of the module produced by `npx likec4 gen react -o src/generated/likec4.mjs .`
 * The generated LikeC4View already has the model provider baked in.
 *
 * We use `any` here because the generated module narrows viewId to specific
 * string literals, which would be incompatible with `string` at the call site.
 */
export interface LikeC4GeneratedModule {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  LikeC4View: React.ComponentType<any>;
}

export interface C4DiagramProps {
  /**
   * The view ID as defined in your .c4 model file.
   * @example viewId="index"
   */
  viewId: string;

  /**
   * Lazy import of the generated module.
   * Generate with: `npx likec4 gen react -o src/generated/likec4.mjs .`
   *
   * @example module={() => import('@site/src/generated/likec4')}
   */
  module?: () => Promise<LikeC4GeneratedModule>;

  /**
   * Height of the diagram in pixels.
   * @default 480
   */
  height?: number;

  /**
   * Optional label shown above the diagram.
   */
  title?: string;

  /**
   * Enable drag-to-pan.
   * @default false
   */
  pannable?: boolean;

  /**
   * Enable scroll-to-zoom.
   * @default false
   */
  zoomable?: boolean;

  /**
   * Background style of the diagram canvas.
   * @default "transparent"
   */
  background?: 'transparent' | 'solid' | 'dots' | 'lines' | 'cross';

  /**
   * Override Docusaurus color mode.
   * By default, follows the user's light/dark preference.
   */
  colorScheme?: 'light' | 'dark';

  className?: string;
}

// ─── Module import cache ─────────────────────────────────────────────────────

// Keyed by the loader function reference so each generated module is loaded once.
const moduleCache = new Map<() => Promise<LikeC4GeneratedModule>, Promise<LikeC4GeneratedModule>>();

function getModule(loader: () => Promise<LikeC4GeneratedModule>): Promise<LikeC4GeneratedModule> {
  if (!moduleCache.has(loader)) {
    moduleCache.set(loader, loader());
  }
  return moduleCache.get(loader)!;
}

// ─── Context — optional global module provider ───────────────────────────────

const C4ModuleContext = createContext<(() => Promise<LikeC4GeneratedModule>) | null>(null);

// ─── Inner component (browser-only) ──────────────────────────────────────────

type LoadState =
  | { status: 'loading' }
  | { status: 'ready'; LikeC4View: LikeC4GeneratedModule['LikeC4View'] }
  | { status: 'error'; message: string };

interface C4DiagramInnerProps extends C4DiagramProps {
  resolvedColorScheme: 'light' | 'dark';
}

function C4DiagramInner({
  viewId,
  module: moduleProp,
  height = 480,
  title,
  pannable = false,
  zoomable = false,
  background = 'transparent',
  resolvedColorScheme,
  className,
}: C4DiagramInnerProps) {
  const contextLoader = useContext(C4ModuleContext);
  const loader = moduleProp ?? contextLoader;

  const [state, setState] = useState<LoadState>({ status: 'loading' });
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!loader) {
      setState({
        status: 'error',
        message:
          'No module provided. Pass `module={() => import("@site/src/generated/likec4")}` as a prop, ' +
          'or wrap your docs with <C4DiagramProvider>.',
      });
      return;
    }

    setState({ status: 'loading' });

    getModule(loader)
      .then((mod) => {
        if (!mountedRef.current) return;
        setState({ status: 'ready', LikeC4View: mod.LikeC4View });
      })
      .catch((err: unknown) => {
        if (!mountedRef.current) return;
        setState({
          status: 'error',
          message: err instanceof Error ? err.message : String(err),
        });
      });
  }, [loader]);

  return (
    <div className={`${styles.wrapper} ${className ?? ''}`}>
      {title && (
        <div className={styles.header}>
          <span className={styles.title}>{title}</span>
          <span className={styles.badge}>C4</span>
        </div>
      )}

      <div className={styles.diagramContainer} style={{ height }}>
        {state.status === 'loading' && (
          <div className={styles.skeleton} style={{ height }}>
            <div className={styles.spinner} />
            <span>Loading diagram…</span>
          </div>
        )}

        {state.status === 'error' && (
          <div className={styles.error}>
            <div className={styles.errorTitle}>Failed to render C4 diagram</div>
            <div className={styles.errorMessage}>{state.message}</div>
          </div>
        )}

        {state.status === 'ready' && (
          <state.LikeC4View
            viewId={viewId}
            pannable={pannable}
            zoomable={zoomable}
            background={background}
            colorScheme={resolvedColorScheme}
            keepAspectRatio={false}
            style={{ width: '100%', height: '100%' }}
          />
        )}
      </div>
    </div>
  );
}

// ─── Public component ─────────────────────────────────────────────────────────

/**
 * Renders a LikeC4 C4 architecture diagram inside a Docusaurus MDX page.
 *
 * Requires a pre-generated module from `npx likec4 gen react`.
 *
 * @example
 * ```mdx
 * import C4Diagram from '@site/src/components/C4Diagram';
 *
 * // Pass the generated module directly:
 * <C4Diagram
 *   viewId="index"
 *   module={() => import('@site/src/generated/likec4')}
 *   title="Landscape View"
 *   height={520}
 * />
 *
 * // Or omit `module` when wrapped by <C4DiagramProvider>:
 * <C4Diagram viewId="index" title="Landscape View" height={520} />
 * ```
 */
export default function C4Diagram(props: C4DiagramProps) {
  return (
    <BrowserOnly fallback={<DiagramSkeleton height={props.height ?? 480} />}>
      {() => {
        // Must be inside BrowserOnly so Docusaurus SSR never sees this hook.
        // eslint-disable-next-line @typescript-eslint/no-var-requires
        const { useColorMode } = require('@docusaurus/theme-common');
        const { colorMode } = useColorMode();
        const resolvedColorScheme =
          props.colorScheme ?? (colorMode === 'dark' ? 'dark' : 'light');
        return <C4DiagramInner {...props} resolvedColorScheme={resolvedColorScheme} />;
      }}
    </BrowserOnly>
  );
}

// ─── Global provider ──────────────────────────────────────────────────────────

export interface C4DiagramProviderProps {
  /**
   * Lazy import of the generated module, evaluated once.
   * @example loader={() => import('@site/src/generated/likec4')}
   */
  loader: () => Promise<LikeC4GeneratedModule>;
  children: React.ReactNode;
}

/**
 * Optional global provider. Place in `src/theme/Root.tsx` so every
 * `<C4Diagram viewId="..." />` in your docs shares one loaded module
 * without passing `module` on each diagram.
 *
 * @example
 * ```tsx
 * // src/theme/Root.tsx
 * import { C4DiagramProvider } from '@site/src/components/C4Diagram';
 *
 * export default function Root({ children }) {
 *   return (
 *     <C4DiagramProvider loader={() => import('@site/src/generated/likec4')}>
 *       {children}
 *     </C4DiagramProvider>
 *   );
 * }
 * ```
 */
export function C4DiagramProvider({ loader, children }: C4DiagramProviderProps) {
  // Kick off the load as early as possible (warm the cache).
  useEffect(() => {
    getModule(loader).catch(() => {
      /* errors surface per-diagram */
    });
  }, [loader]);

  return (
    <C4ModuleContext.Provider value={loader}>
      {children}
    </C4ModuleContext.Provider>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function DiagramSkeleton({ height }: { height: number }) {
  return (
    <div className={styles.skeleton} style={{ height }}>
      <div className={styles.spinner} />
      <span>Loading diagram…</span>
    </div>
  );
}
