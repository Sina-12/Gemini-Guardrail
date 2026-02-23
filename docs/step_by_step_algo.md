## Step-by-step algorithm for corpus collection

1. **Define the data source**  
   Select a Reddit discussion thread and access it using its JSON endpoint:  
   `https://old.reddit.com/comments/<post_id>.json`  
   This returns structured data that is easier to process than HTML.

2. **Send a request to the server**  
   Use the `requests` library to send an HTTP GET request with a User-Agent header so the request is not blocked.

   Documentation: https://docs.python-requests.org/

3. **Check the response status**  
   Verify that the server returns status code `200`.  
   If the request fails, stop the script and print an error message to avoid saving invalid data.

4. **Convert the response to Python format**  
   Use `response.json()` to convert the JSON content into a Python object so the thread structure can be accessed.

5. **Extract the text of one document**  
   Navigate through the nested Reddit data and select the comment body.  
   Each comment is treated as one corpus document (one instance).

6. **Create the output directory if needed**  
   Automatically create the `data/raw/` folder so the script works on a fresh clone of the repository.

7. **Save the document in structured format**  
   Store the extracted text in a JSON file.  
   This format allows metadata and annotation layers to be added later without modifying the original text.

8. **Scale to the full corpus (future step)**  
   For the complete corpus, this process will be repeated for many post IDs to collect a large number of documents and reach the target corpus size.

---

## Data source

Reddit API / JSON structure:  
https://www.reddit.com/dev/api/