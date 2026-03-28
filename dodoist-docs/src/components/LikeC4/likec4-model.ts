/* prettier-ignore-start */
/* eslint-disable */

/******************************************************************************
 * This file was generated
 * DO NOT EDIT MANUALLY!
 ******************************************************************************/

import { LikeC4Model } from 'likec4/model'
import type { Aux, SpecAux } from 'likec4/model';

export type $Specs = SpecAux<
  // Element kinds
  | "actor"
  | "component"
  | "system",
  // Deployment kinds
  never,
  // Relationship kinds
  never,
  // Tags
  never,
  // Metadata keys
  never
>

export type $Aux = Aux<
  "layouted",
  // Elements
  | "customer"
  | "saas"
  | "saas.backend"
  | "saas.ui",
  // Deployments
  never,
  // Views
  | "__customer"
  | "__saas_backend"
  | "__saas_ui"
  | "index"
  | "view_zr8dk6",
  // Project ID
  "default",
  $Specs
>

export type $ElementId = $Aux['ElementId']
export type $DeploymentId = $Aux['DeploymentId']
export type $ViewId = $Aux['ViewId']

export type $ElementKind = $Aux['ElementKind']
export type $RelationKind = $Aux['RelationKind']
export type $DeploymentKind = $Aux['DeploymentKind']
export type $Tag = $Aux['Tag']
export type $Tags = readonly $Aux['Tag'][]
export type $MetadataKey = $Aux['MetadataKey']


export const likec4model: LikeC4Model<$Aux> = new LikeC4Model({
  _stage: 'layouted',
  projectId: 'default',
  project: {
    id: 'default',
    title: 'default',
  },
  specification: {
    tags: {},
    elements: {
      actor: {
        style: {},
      },
      system: {
        style: {},
      },
      component: {
        style: {},
      },
    },
    relationships: {},
    deployments: {},
    customColors: {},
  },
  elements: {
    customer: {
      style: {},
      description: {
        txt: 'Our dear customer',
      },
      title: 'Customer',
      kind: 'actor',
      id: 'customer',
    },
    saas: {
      style: {},
      title: 'Our SaaS',
      kind: 'system',
      id: 'saas',
    },
    'saas.ui': {
      style: {
        icon: 'tech:nextjs',
        shape: 'browser',
      },
      technology: 'Nextjs',
      description: {
        txt: 'Nextjs application, hosted on Vercel',
      },
      title: 'Frontend',
      kind: 'component',
      id: 'saas.ui',
    },
    'saas.backend': {
      style: {},
      description: {
        txt: 'Implements business logic\nand exposes as REST API',
      },
      title: 'Backend Services',
      kind: 'component',
      id: 'saas.backend',
    },
  },
  relations: {
    '1mhdeao': {
      title: 'opens in browser',
      source: {
        model: 'customer',
      },
      target: {
        model: 'saas.ui',
      },
      id: '1mhdeao',
    },
    '1437bxv': {
      title: 'enjoys our product',
      source: {
        model: 'customer',
      },
      target: {
        model: 'saas',
      },
      id: '1437bxv',
    },
    azx0aq: {
      title: 'fetches via HTTPS',
      source: {
        model: 'saas.ui',
      },
      target: {
        model: 'saas.backend',
      },
      id: 'azx0aq',
    },
  },
  globals: {
    predicates: {},
    dynamicPredicates: {},
    styles: {},
  },
  views: {
    index: {
      _type: 'element',
      tags: null,
      links: null,
      _stage: 'layouted',
      sourcePath: 'docs/architecture/model.c4',
      description: null,
      title: 'Landscape view',
      id: 'index',
      autoLayout: {
        direction: 'TB',
      },
      hash: 'dAgSEZicMFMPCOI4-EI744oq0_s9RZUL_cIFAkKZGys',
      bounds: {
        x: 0,
        y: 0,
        width: 320,
        height: 503,
      },
      nodes: [
        {
          id: 'customer',
          parent: null,
          level: 0,
          children: [],
          inEdges: [],
          outEdges: [
            'm64d1q',
          ],
          title: 'Customer',
          modelRef: 'customer',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Our dear customer',
          },
          tags: [],
          kind: 'actor',
          navigateTo: '__customer',
          x: 0,
          y: 0,
          width: 320,
          height: 180,
          labelBBox: {
            x: 96,
            y: 63,
            width: 129,
            height: 48,
          },
        },
        {
          id: 'saas',
          parent: null,
          level: 0,
          children: [],
          inEdges: [
            'm64d1q',
          ],
          outEdges: [],
          title: 'Our SaaS',
          modelRef: 'saas',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          tags: [],
          kind: 'system',
          navigateTo: 'view_zr8dk6',
          x: 0,
          y: 323,
          width: 320,
          height: 180,
          labelBBox: {
            x: 114,
            y: 74,
            width: 92,
            height: 24,
          },
        },
      ],
      edges: [
        {
          id: 'm64d1q',
          source: 'customer',
          target: 'saas',
          label: 'enjoys our product',
          points: [
            [
              160,
              180,
            ],
            [
              160,
              221,
            ],
            [
              160,
              270,
            ],
            [
              160,
              313,
            ],
          ],
          labelBBox: {
            x: 161,
            y: 240,
            width: 119,
            height: 18,
          },
          parent: null,
          relations: [
            '1mhdeao',
            '1437bxv',
          ],
          color: 'gray',
          line: 'dashed',
          head: 'normal',
        },
      ],
    },
    view_zr8dk6: {
      _type: 'element',
      tags: null,
      links: null,
      viewOf: 'saas',
      _stage: 'layouted',
      sourcePath: 'docs/architecture/model.c4',
      description: null,
      title: 'Our SaaS',
      id: 'view_zr8dk6',
      autoLayout: {
        direction: 'TB',
      },
      hash: 'IGuAx1c967O6BxgdpgZ-09lv1KupxC2RqcWb4BPcJ2E',
      bounds: {
        x: 0,
        y: 0,
        width: 969,
        height: 560,
      },
      nodes: [
        {
          id: 'customer',
          parent: null,
          level: 0,
          children: [],
          inEdges: [],
          outEdges: [
            '15thye4',
          ],
          title: 'Customer',
          modelRef: 'customer',
          shape: 'rectangle',
          color: 'muted',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Our dear customer',
          },
          tags: [],
          kind: 'actor',
          navigateTo: '__customer',
          x: 48,
          y: 0,
          width: 320,
          height: 180,
          labelBBox: {
            x: 95,
            y: 63,
            width: 129,
            height: 48,
          },
        },
        {
          id: 'saas',
          parent: null,
          level: 0,
          children: [
            'saas.ui',
            'saas.backend',
          ],
          inEdges: [
            '15thye4',
          ],
          outEdges: [],
          title: 'Our SaaS',
          modelRef: 'saas',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          tags: [],
          kind: 'system',
          depth: 1,
          x: 8,
          y: 271,
          width: 953,
          height: 281,
          labelBBox: {
            x: 6,
            y: 0,
            width: 62,
            height: 15,
          },
        },
        {
          id: 'saas.ui',
          parent: 'saas',
          level: 1,
          children: [],
          inEdges: [
            '15thye4',
          ],
          outEdges: [
            '1kezxci',
          ],
          title: 'Frontend',
          modelRef: 'saas.ui',
          shape: 'browser',
          color: 'primary',
          icon: 'tech:nextjs',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Nextjs application, hosted on Vercel',
          },
          tags: [],
          technology: 'Nextjs',
          kind: 'component',
          navigateTo: '__saas_ui',
          x: 48,
          y: 332,
          width: 320,
          height: 180,
          labelBBox: {
            x: 48,
            y: 44,
            width: 254,
            height: 85,
          },
        },
        {
          id: 'saas.backend',
          parent: 'saas',
          level: 1,
          children: [],
          inEdges: [
            '1kezxci',
          ],
          outEdges: [],
          title: 'Backend Services',
          modelRef: 'saas.backend',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Implements business logic\nand exposes as REST API',
          },
          tags: [],
          kind: 'component',
          navigateTo: '__saas_backend',
          x: 601,
          y: 332,
          width: 320,
          height: 180,
          labelBBox: {
            x: 69,
            y: 54,
            width: 182,
            height: 66,
          },
        },
      ],
      edges: [
        {
          id: '15thye4',
          source: 'customer',
          target: 'saas.ui',
          label: 'opens in browser',
          points: [
            [
              208,
              180,
            ],
            [
              208,
              224,
            ],
            [
              208,
              277,
            ],
            [
              208,
              322,
            ],
          ],
          labelBBox: {
            x: 209,
            y: 240,
            width: 111,
            height: 18,
          },
          parent: null,
          relations: [
            '1mhdeao',
          ],
          color: 'gray',
          line: 'dashed',
          head: 'normal',
        },
        {
          id: '1kezxci',
          source: 'saas.ui',
          target: 'saas.backend',
          label: 'fetches via HTTPS',
          points: [
            [
              368,
              422,
            ],
            [
              438,
              422,
            ],
            [
              520,
              422,
            ],
            [
              591,
              422,
            ],
          ],
          labelBBox: {
            x: 424,
            y: 396,
            width: 121,
            height: 18,
          },
          parent: 'saas',
          relations: [
            'azx0aq',
          ],
          color: 'gray',
          line: 'dashed',
          head: 'normal',
        },
      ],
    },
    __customer: {
      _stage: 'layouted',
      _type: 'element',
      id: '__customer',
      viewOf: 'customer',
      title: 'Auto / Customer',
      description: null,
      autoLayout: {
        direction: 'TB',
      },
      hash: 'whE1Zu6h56DAKWO_Qumx-E3RvpkY9NO2fdlW9m0-l3I',
      bounds: {
        x: 0,
        y: 0,
        width: 320,
        height: 503,
      },
      nodes: [
        {
          id: 'customer',
          parent: null,
          level: 0,
          children: [],
          inEdges: [],
          outEdges: [
            'm64d1q',
          ],
          title: 'Customer',
          modelRef: 'customer',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Our dear customer',
          },
          tags: [],
          kind: 'actor',
          x: 0,
          y: 0,
          width: 320,
          height: 180,
          labelBBox: {
            x: 96,
            y: 63,
            width: 129,
            height: 48,
          },
        },
        {
          id: 'saas',
          parent: null,
          level: 0,
          children: [],
          inEdges: [
            'm64d1q',
          ],
          outEdges: [],
          title: 'Our SaaS',
          modelRef: 'saas',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          tags: [],
          kind: 'system',
          navigateTo: 'view_zr8dk6',
          x: 0,
          y: 323,
          width: 320,
          height: 180,
          labelBBox: {
            x: 114,
            y: 74,
            width: 92,
            height: 24,
          },
        },
      ],
      edges: [
        {
          id: 'm64d1q',
          source: 'customer',
          target: 'saas',
          label: 'enjoys our product',
          points: [
            [
              160,
              180,
            ],
            [
              160,
              221,
            ],
            [
              160,
              270,
            ],
            [
              160,
              313,
            ],
          ],
          labelBBox: {
            x: 161,
            y: 240,
            width: 119,
            height: 18,
          },
          parent: null,
          relations: [
            '1mhdeao',
            '1437bxv',
          ],
          color: 'gray',
          line: 'dashed',
          head: 'normal',
        },
      ],
    },
    __saas_ui: {
      _stage: 'layouted',
      _type: 'element',
      id: '__saas_ui',
      viewOf: 'saas.ui',
      title: 'Auto / Frontend',
      description: null,
      autoLayout: {
        direction: 'TB',
      },
      hash: 'oILcjIhaoQN0QUdNelyb0i9ndXAxEY2ppEvPomHx4oY',
      bounds: {
        x: 0,
        y: 0,
        width: 320,
        height: 826,
      },
      nodes: [
        {
          id: 'customer',
          parent: null,
          level: 0,
          children: [],
          inEdges: [],
          outEdges: [
            '15thye4',
          ],
          title: 'Customer',
          modelRef: 'customer',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Our dear customer',
          },
          tags: [],
          kind: 'actor',
          navigateTo: '__customer',
          x: 0,
          y: 0,
          width: 320,
          height: 180,
          labelBBox: {
            x: 96,
            y: 63,
            width: 129,
            height: 48,
          },
        },
        {
          id: 'saas.ui',
          parent: null,
          level: 0,
          children: [],
          inEdges: [
            '15thye4',
          ],
          outEdges: [
            '1kezxci',
          ],
          title: 'Frontend',
          modelRef: 'saas.ui',
          shape: 'browser',
          color: 'primary',
          icon: 'tech:nextjs',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Nextjs application, hosted on Vercel',
          },
          tags: [],
          technology: 'Nextjs',
          kind: 'component',
          x: 0,
          y: 323,
          width: 320,
          height: 180,
          labelBBox: {
            x: 48,
            y: 44,
            width: 254,
            height: 85,
          },
        },
        {
          id: 'saas.backend',
          parent: null,
          level: 0,
          children: [],
          inEdges: [
            '1kezxci',
          ],
          outEdges: [],
          title: 'Backend Services',
          modelRef: 'saas.backend',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Implements business logic\nand exposes as REST API',
          },
          tags: [],
          kind: 'component',
          navigateTo: '__saas_backend',
          x: 0,
          y: 646,
          width: 320,
          height: 180,
          labelBBox: {
            x: 69,
            y: 54,
            width: 182,
            height: 65,
          },
        },
      ],
      edges: [
        {
          id: '15thye4',
          source: 'customer',
          target: 'saas.ui',
          label: 'opens in browser',
          points: [
            [
              160,
              180,
            ],
            [
              160,
              221,
            ],
            [
              160,
              270,
            ],
            [
              160,
              313,
            ],
          ],
          labelBBox: {
            x: 161,
            y: 240,
            width: 111,
            height: 18,
          },
          parent: null,
          relations: [
            '1mhdeao',
          ],
          color: 'gray',
          line: 'dashed',
          head: 'normal',
        },
        {
          id: '1kezxci',
          source: 'saas.ui',
          target: 'saas.backend',
          label: 'fetches via HTTPS',
          points: [
            [
              160,
              503,
            ],
            [
              160,
              544,
            ],
            [
              160,
              593,
            ],
            [
              160,
              635,
            ],
          ],
          labelBBox: {
            x: 161,
            y: 562,
            width: 121,
            height: 18,
          },
          parent: null,
          relations: [
            'azx0aq',
          ],
          color: 'gray',
          line: 'dashed',
          head: 'normal',
        },
      ],
    },
    __saas_backend: {
      _stage: 'layouted',
      _type: 'element',
      id: '__saas_backend',
      viewOf: 'saas.backend',
      title: 'Auto / Backend Services',
      description: null,
      autoLayout: {
        direction: 'TB',
      },
      hash: 'pRXoFT04ZRgRL2ttz8E4nR4ViIB3pPvS6Tdwu-avTfI',
      bounds: {
        x: 0,
        y: 0,
        width: 320,
        height: 503,
      },
      nodes: [
        {
          id: 'saas.ui',
          parent: null,
          level: 0,
          children: [],
          inEdges: [],
          outEdges: [
            '1kezxci',
          ],
          title: 'Frontend',
          modelRef: 'saas.ui',
          shape: 'browser',
          color: 'primary',
          icon: 'tech:nextjs',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Nextjs application, hosted on Vercel',
          },
          tags: [],
          technology: 'Nextjs',
          kind: 'component',
          navigateTo: '__saas_ui',
          x: 0,
          y: 0,
          width: 320,
          height: 180,
          labelBBox: {
            x: 48,
            y: 44,
            width: 254,
            height: 85,
          },
        },
        {
          id: 'saas.backend',
          parent: null,
          level: 0,
          children: [],
          inEdges: [
            '1kezxci',
          ],
          outEdges: [],
          title: 'Backend Services',
          modelRef: 'saas.backend',
          shape: 'rectangle',
          color: 'primary',
          style: {
            opacity: 15,
            size: 'md',
          },
          description: {
            txt: 'Implements business logic\nand exposes as REST API',
          },
          tags: [],
          kind: 'component',
          x: 0,
          y: 323,
          width: 320,
          height: 180,
          labelBBox: {
            x: 69,
            y: 54,
            width: 182,
            height: 65,
          },
        },
      ],
      edges: [
        {
          id: '1kezxci',
          source: 'saas.ui',
          target: 'saas.backend',
          label: 'fetches via HTTPS',
          points: [
            [
              160,
              180,
            ],
            [
              160,
              221,
            ],
            [
              160,
              270,
            ],
            [
              160,
              313,
            ],
          ],
          labelBBox: {
            x: 161,
            y: 240,
            width: 121,
            height: 18,
          },
          parent: null,
          relations: [
            'azx0aq',
          ],
          color: 'gray',
          line: 'dashed',
          head: 'normal',
        },
      ],
    },
  },
  deployments: {
    elements: {},
    relations: {},
  },
  imports: {},
  manualLayouts: {},
} as any) as any

/* prettier-ignore-end */
