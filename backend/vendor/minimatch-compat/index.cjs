'use strict';

// API adapter only: all pattern compilation/matching is upstream minimatch 11.
const engine = require('minimatch-engine');

function normalize(pattern) {
  if (typeof pattern !== 'string') throw new TypeError('invalid pattern');
  if (pattern.length > 65536) throw new TypeError('pattern is too long');
  return pattern.trim(); // minimatch 3's constructor trimmed patterns.
}

function adapter(defaults = {}) {
  const optionsFor = options => ({ optimizationLevel: 0, ...defaults, ...options });

  function Minimatch(pattern, options) {
    if (!(this instanceof Minimatch)) return new Minimatch(pattern, options);
    const compiled = new engine.Minimatch(normalize(pattern), optionsFor(options));
    Object.defineProperty(this, '_compiled', { value: compiled });
    for (const key of ['options', 'pattern', 'negate', 'comment', 'empty', 'partial', 'globSet', 'globParts']) {
      this[key] = compiled[key];
    }
    // glob 7 reads _glob and uses String.match on each non-literal segment.
    // Do not turn the fixed nonrecursive matcher back into a regular expression.
    this.set = compiled.set.map((row, i) => row.map((part, j) => {
      if (typeof part === 'string' || part === engine.GLOBSTAR) return part;
      return {
        _glob: compiled.globParts[i][j],
        [Symbol.match](value) { return part.test(value) ? [value] : null; },
      };
    }));
  }
  Minimatch.prototype.match = function (value, partial) {
    return this._compiled.match(value, partial);
  };
  Minimatch.prototype.braceExpand = function () {
    return this._compiled.braceExpand();
  };
  Minimatch.GLOBSTAR = engine.GLOBSTAR;
  Minimatch.defaults = options => adapter({ ...defaults, ...options }).Minimatch;

  function minimatch(value, pattern, options) {
    return new Minimatch(pattern, options).match(value);
  }
  minimatch.Minimatch = Minimatch;
  minimatch.GLOBSTAR = engine.GLOBSTAR;
  minimatch.sep = engine.sep;
  minimatch.defaults = options => adapter({ ...defaults, ...options });
  minimatch.filter = (pattern, options) => value => minimatch(value, pattern, options);
  minimatch.braceExpand = (pattern, options) => engine.braceExpand(pattern, optionsFor(options));
  minimatch.match = (values, pattern, options) => {
    const compiled = new Minimatch(pattern, options);
    const matches = values.filter(value => compiled.match(value));
    if (compiled.options.nonull && !matches.length) matches.push(pattern);
    return matches;
  };
  return minimatch;
}

module.exports = adapter();
