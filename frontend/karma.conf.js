/**
 * karma.conf.js
 *
 * Purpose:
 *   Configures the unit test runner of the Angular application: compiles the
 *   spec files with the Angular builder, runs them with Jasmine inside a
 *   headless Chrome instance and collects the coverage report.
 *
 * Input:
 *   - The spec files matched by tsconfig.spec.json.
 *   - The CHROME_BIN environment variable when Chrome is not in the default path.
 *
 * Output:
 *   - Test results in the terminal and an optional HTML coverage report in
 *     ./coverage/nuevamente-frontend.
 */

module.exports = function (config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine', '@angular-devkit/build-angular'],
    plugins: [
      require('karma-jasmine'),
      require('karma-chrome-launcher'),
      require('karma-jasmine-html-reporter'),
      require('karma-coverage'),
      require('@angular-devkit/build-angular/plugins/karma'),
    ],
    client: {
      jasmine: {
        random: false,
      },
      clearContext: false,
    },
    jasmineHtmlReporter: {
      suppressAll: true,
    },
    coverageReporter: {
      dir: require('path').join(__dirname, './coverage/nuevamente-frontend'),
      subdir: '.',
      reporters: [{ type: 'html' }, { type: 'text-summary' }],
    },
    reporters: ['progress', 'kjhtml'],
    browsers: ['ChromeHeadlessNoSandbox'],
    customLaunchers: {
      ChromeHeadlessNoSandbox: {
        base: 'ChromeHeadless',
        flags: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
      },
    },
    restartOnFileChange: true,
  });
};
