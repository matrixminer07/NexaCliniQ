const API_BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:5000';

type ApiRequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown;
};

export const apiRequest = async (endpoint: string, options: ApiRequestOptions = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  const { body, ...restOptions } = options;
  
  const defaultOptions: RequestInit = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    ...restOptions,
  };

  // If body is provided, ensure it's stringified
  if (body !== undefined) {
    defaultOptions.body =
      typeof body === 'string' || body instanceof FormData
        ? body
        : JSON.stringify(body);
  }

  try {
    const response = await fetch(url, defaultOptions);
    
    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API Request Error:', error);
    throw error;
  }
};

export const apiPost = async (endpoint: string, data: unknown) => {
  return apiRequest(endpoint, {
    method: 'POST',
    body: data,
  });
};

export const apiGet = async (endpoint: string) => {
  return apiRequest(endpoint, {
    method: 'GET',
  });
};
