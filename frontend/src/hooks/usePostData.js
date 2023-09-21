import { useEffect, useState } from 'react';
import { postData } from '../api/handleRequests';

export function usePostData(apiEndpoint) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function postDataApi() {
      try {
        const response = await postData(apiEndpoint);
        setData(response.data);
      } catch (error) {
        setError(error);
      } finally {
        setIsLoading(false);
      }
    }

    postDataApi();
  }, [apiEndpoint]);

  return { data, isLoading, error };
}