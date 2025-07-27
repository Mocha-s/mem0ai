import type { Preview } from '@storybook/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import '../app/globals.css';

// Mock Redux store for Storybook
const mockStore = configureStore({
  reducer: {
    profile: (state = { userId: 'storybook-user' }) => state,
  },
});

// Mock MSW for Storybook
import { initialize, mswLoader } from 'msw-storybook-addon';
import { openMemoryHandlers } from '../src/mocks/handlers/openmemory';
import { mem0Handlers } from '../src/mocks/handlers/mem0';

// Initialize MSW
initialize({
  onUnhandledRequest: 'bypass',
});

const preview: Preview = {
  parameters: {
    actions: { argTypesRegex: '^on[A-Z].*' },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    docs: {
      toc: true,
    },
    layout: 'centered',
    backgrounds: {
      default: 'light',
      values: [
        {
          name: 'light',
          value: '#ffffff',
        },
        {
          name: 'dark',
          value: '#0f172a',
        },
        {
          name: 'gray',
          value: '#f8fafc',
        },
      ],
    },
    viewport: {
      viewports: {
        mobile: {
          name: 'Mobile',
          styles: {
            width: '375px',
            height: '667px',
          },
        },
        tablet: {
          name: 'Tablet',
          styles: {
            width: '768px',
            height: '1024px',
          },
        },
        desktop: {
          name: 'Desktop',
          styles: {
            width: '1024px',
            height: '768px',
          },
        },
        wide: {
          name: 'Wide',
          styles: {
            width: '1440px',
            height: '900px',
          },
        },
      },
    },
    msw: {
      handlers: [...openMemoryHandlers, ...mem0Handlers],
    },
  },
  decorators: [
    (Story) => (
      <Provider store={mockStore}>
        <div className="font-sans antialiased">
          <Story />
        </div>
      </Provider>
    ),
  ],
  loaders: [mswLoader],
  tags: ['autodocs'],
};

export default preview;
