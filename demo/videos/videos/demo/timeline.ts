import type { Timeline } from 'videowright';
import '../../styles/onme/tokens.css';
import intro from './segments/intro/index.js';
import setup from './segments/setup/index.js';
import fault from './segments/fault/index.js';
import triage from './segments/triage/index.js';
import diagnosis from './segments/diagnosis/index.js';
import patch from './segments/patch/index.js';
import sandbox from './segments/sandbox/index.js';
import pr from './segments/pr/index.js';
import outro from './segments/outro/index.js';

export default {
  meta: {
    title: 'Mender demo — from broken service to verified PR',
    style: 'onme',
  },
  segments: [
    intro,
    setup,
    fault,
    triage,
    diagnosis,
    patch,
    sandbox,
    pr,
    outro,
  ],
} satisfies Timeline;
