// Test Runner Script
import { execSync } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';

interface TestConfig {
  testMatch: string[];
  coverage: boolean;
  watch: boolean;
  verbose: boolean;
  silent: boolean;
}

class TestRunner {
  private config: TestConfig;

  constructor(config: Partial<TestConfig> = {}) {
    this.config = {
      testMatch: ['**/__tests__/**/*.test.{ts,tsx}'],
      coverage: false,
      watch: false,
      verbose: false,
      silent: false,
      ...config,
    };
  }

  /**
   * Run all tests
   */
  async runAll(): Promise<void> {
    console.log('🧪 Running all tests...');
    
    try {
      const command = this.buildJestCommand();
      execSync(command, { stdio: 'inherit' });
      console.log('✅ All tests passed!');
    } catch (error) {
      console.error('❌ Some tests failed');
      process.exit(1);
    }
  }

  /**
   * Run specific test file
   */
  async runFile(filePath: string): Promise<void> {
    if (!existsSync(filePath)) {
      console.error(`❌ Test file not found: ${filePath}`);
      process.exit(1);
    }

    console.log(`🧪 Running test file: ${filePath}`);
    
    try {
      const command = this.buildJestCommand([filePath]);
      execSync(command, { stdio: 'inherit' });
      console.log('✅ Test file passed!');
    } catch (error) {
      console.error('❌ Test file failed');
      process.exit(1);
    }
  }

  /**
   * Run tests by pattern
   */
  async runPattern(pattern: string): Promise<void> {
    console.log(`🧪 Running tests matching pattern: ${pattern}`);
    
    try {
      const command = this.buildJestCommand([], pattern);
      execSync(command, { stdio: 'inherit' });
      console.log('✅ Pattern tests passed!');
    } catch (error) {
      console.error('❌ Pattern tests failed');
      process.exit(1);
    }
  }

  /**
   * Run tests with coverage
   */
  async runWithCoverage(): Promise<void> {
    console.log('🧪 Running tests with coverage...');
    
    this.config.coverage = true;
    
    try {
      const command = this.buildJestCommand();
      execSync(command, { stdio: 'inherit' });
      console.log('✅ Tests with coverage completed!');
    } catch (error) {
      console.error('❌ Tests with coverage failed');
      process.exit(1);
    }
  }

  /**
   * Run tests in watch mode
   */
  async runWatch(): Promise<void> {
    console.log('🧪 Running tests in watch mode...');
    
    this.config.watch = true;
    
    try {
      const command = this.buildJestCommand();
      execSync(command, { stdio: 'inherit' });
    } catch (error) {
      console.error('❌ Watch mode failed');
      process.exit(1);
    }
  }

  /**
   * Run unit tests only
   */
  async runUnitTests(): Promise<void> {
    console.log('🧪 Running unit tests...');
    await this.runPattern('unit');
  }

  /**
   * Run integration tests only
   */
  async runIntegrationTests(): Promise<void> {
    console.log('🧪 Running integration tests...');
    await this.runPattern('integration');
  }

  /**
   * Run API tests only
   */
  async runApiTests(): Promise<void> {
    console.log('🧪 Running API tests...');
    await this.runPattern('api');
  }

  /**
   * Run hook tests only
   */
  async runHookTests(): Promise<void> {
    console.log('🧪 Running hook tests...');
    await this.runPattern('hooks');
  }

  /**
   * Build Jest command
   */
  private buildJestCommand(files: string[] = [], pattern?: string): string {
    const parts = ['npx jest'];

    // Add test files
    if (files.length > 0) {
      parts.push(...files);
    }

    // Add pattern
    if (pattern) {
      parts.push(`--testNamePattern="${pattern}"`);
    }

    // Add coverage
    if (this.config.coverage) {
      parts.push('--coverage');
      parts.push('--coverageDirectory=coverage');
      parts.push('--coverageReporters=text,lcov,html');
    }

    // Add watch mode
    if (this.config.watch) {
      parts.push('--watch');
    }

    // Add verbose mode
    if (this.config.verbose) {
      parts.push('--verbose');
    }

    // Add silent mode
    if (this.config.silent) {
      parts.push('--silent');
    }

    // Add test match patterns
    if (this.config.testMatch.length > 0) {
      const testMatch = this.config.testMatch.map(pattern => `"${pattern}"`).join(',');
      parts.push(`--testMatch=[${testMatch}]`);
    }

    return parts.join(' ');
  }

  /**
   * Check test environment
   */
  checkEnvironment(): void {
    console.log('🔍 Checking test environment...');

    // Check if Jest is available
    try {
      execSync('npx jest --version', { stdio: 'pipe' });
      console.log('✅ Jest is available');
    } catch (error) {
      console.error('❌ Jest is not available');
      process.exit(1);
    }

    // Check if test files exist
    const testDirs = ['__tests__', 'src/__tests__'];
    const hasTests = testDirs.some(dir => existsSync(path.join(process.cwd(), dir)));
    
    if (hasTests) {
      console.log('✅ Test files found');
    } else {
      console.warn('⚠️ No test files found');
    }

    // Check if setup file exists
    const setupFile = path.join(process.cwd(), '__tests__/setup.ts');
    if (existsSync(setupFile)) {
      console.log('✅ Test setup file found');
    } else {
      console.warn('⚠️ Test setup file not found');
    }

    console.log('✅ Environment check completed');
  }

  /**
   * Generate test report
   */
  async generateReport(): Promise<void> {
    console.log('📊 Generating test report...');
    
    try {
      const command = this.buildJestCommand();
      const output = execSync(`${command} --json`, { encoding: 'utf8' });
      const report = JSON.parse(output);
      
      console.log('📊 Test Report:');
      console.log(`Total Tests: ${report.numTotalTests}`);
      console.log(`Passed: ${report.numPassedTests}`);
      console.log(`Failed: ${report.numFailedTests}`);
      console.log(`Skipped: ${report.numPendingTests}`);
      console.log(`Success Rate: ${((report.numPassedTests / report.numTotalTests) * 100).toFixed(2)}%`);
      
      if (report.numFailedTests > 0) {
        console.log('\n❌ Failed Tests:');
        report.testResults.forEach((result: any) => {
          if (result.status === 'failed') {
            console.log(`  - ${result.name}`);
          }
        });
      }
    } catch (error) {
      console.error('❌ Failed to generate test report');
    }
  }
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  const command = args[0];
  const runner = new TestRunner();

  switch (command) {
    case 'all':
      runner.runAll();
      break;
    case 'file':
      if (args[1]) {
        runner.runFile(args[1]);
      } else {
        console.error('❌ Please provide a file path');
        process.exit(1);
      }
      break;
    case 'pattern':
      if (args[1]) {
        runner.runPattern(args[1]);
      } else {
        console.error('❌ Please provide a pattern');
        process.exit(1);
      }
      break;
    case 'coverage':
      runner.runWithCoverage();
      break;
    case 'watch':
      runner.runWatch();
      break;
    case 'unit':
      runner.runUnitTests();
      break;
    case 'integration':
      runner.runIntegrationTests();
      break;
    case 'api':
      runner.runApiTests();
      break;
    case 'hooks':
      runner.runHookTests();
      break;
    case 'check':
      runner.checkEnvironment();
      break;
    case 'report':
      runner.generateReport();
      break;
    default:
      console.log('🧪 Test Runner Commands:');
      console.log('  all         - Run all tests');
      console.log('  file <path> - Run specific test file');
      console.log('  pattern <p> - Run tests matching pattern');
      console.log('  coverage    - Run tests with coverage');
      console.log('  watch       - Run tests in watch mode');
      console.log('  unit        - Run unit tests only');
      console.log('  integration - Run integration tests only');
      console.log('  api         - Run API tests only');
      console.log('  hooks       - Run hook tests only');
      console.log('  check       - Check test environment');
      console.log('  report      - Generate test report');
      break;
  }
}

export { TestRunner };
