module.exports = function (plop) {
  // Component generator
  plop.setGenerator('component', {
    description: 'Create a new React component',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Component name:',
        validate: function (value) {
          if (/.+/.test(value)) {
            return true;
          }
          return 'Component name is required';
        },
      },
      {
        type: 'list',
        name: 'type',
        message: 'Component type:',
        choices: ['ui', 'mem0', 'common', 'mcp'],
        default: 'common',
      },
      {
        type: 'confirm',
        name: 'withStory',
        message: 'Create Storybook story?',
        default: true,
      },
      {
        type: 'confirm',
        name: 'withTest',
        message: 'Create test file?',
        default: true,
      },
    ],
    actions: function (data) {
      const actions = [];
      
      // Create component file
      actions.push({
        type: 'add',
        path: 'components/{{type}}/{{pascalCase name}}/{{pascalCase name}}.tsx',
        templateFile: 'plop-templates/component.hbs',
      });
      
      // Create index file
      actions.push({
        type: 'add',
        path: 'components/{{type}}/{{pascalCase name}}/index.ts',
        templateFile: 'plop-templates/index.hbs',
      });
      
      // Create story file if requested
      if (data.withStory) {
        actions.push({
          type: 'add',
          path: 'stories/{{pascalCase name}}.stories.ts',
          templateFile: 'plop-templates/story.hbs',
        });
      }
      
      // Create test file if requested
      if (data.withTest) {
        actions.push({
          type: 'add',
          path: '__tests__/components/{{pascalCase name}}.test.tsx',
          templateFile: 'plop-templates/test.hbs',
        });
      }
      
      return actions;
    },
  });

  // Hook generator
  plop.setGenerator('hook', {
    description: 'Create a new React hook',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'Hook name (without "use" prefix):',
        validate: function (value) {
          if (/.+/.test(value)) {
            return true;
          }
          return 'Hook name is required';
        },
      },
      {
        type: 'confirm',
        name: 'withTest',
        message: 'Create test file?',
        default: true,
      },
    ],
    actions: function (data) {
      const actions = [];
      
      // Create hook file
      actions.push({
        type: 'add',
        path: 'hooks/use{{pascalCase name}}.ts',
        templateFile: 'plop-templates/hook.hbs',
      });
      
      // Create test file if requested
      if (data.withTest) {
        actions.push({
          type: 'add',
          path: '__tests__/hooks/use{{pascalCase name}}.test.ts',
          templateFile: 'plop-templates/hook-test.hbs',
        });
      }
      
      return actions;
    },
  });

  // API Client generator
  plop.setGenerator('api-client', {
    description: 'Create a new API client',
    prompts: [
      {
        type: 'input',
        name: 'name',
        message: 'API Client name:',
        validate: function (value) {
          if (/.+/.test(value)) {
            return true;
          }
          return 'API Client name is required';
        },
      },
    ],
    actions: [
      {
        type: 'add',
        path: 'lib/{{kebabCase name}}-client/index.ts',
        templateFile: 'plop-templates/api-client.hbs',
      },
      {
        type: 'add',
        path: 'lib/{{kebabCase name}}-client/types.ts',
        templateFile: 'plop-templates/api-types.hbs',
      },
      {
        type: 'add',
        path: '__tests__/lib/{{kebabCase name}}-client.test.ts',
        templateFile: 'plop-templates/api-test.hbs',
      },
    ],
  });
};
