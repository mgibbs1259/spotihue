import { useEffect, useState } from 'react';
import { getData } from '../api/handleRequests';

export function useGetData(apiEndpoint) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function getDataApi() {
      try {
        const response = await getData(apiEndpoint);
        setData(response);
      } catch (error) {
        setError(error);
      } finally {
        setIsLoading(false);
      }
    }

    getDataApi();
  }, [apiEndpoint]);
  
  return { data, isLoading, error };
}