# Argument Summaries Instructions

## Files included

- `argument-summaries-app.tar`
- `argument-summaries-instructions.md`

## How to run the app

### 1  Load the Docker image

Open a terminal in the folder containing `argument-summaries-app.tar` AND make sure the docker application is open while running the commands:

```bash
docker load -i argument-summaries-app.tar
```

###2  Run the Docker container

```bash
docker run --rm -p 8000:8000 argument-summaries-app
```

###3  Open the interface
Open this URL in your browser:

http://localhost:8000

- How to stop the app:

    In the terminal where the container is running, press Ctrl + C.



### What peer reviewers should test:

Please try the following when testing the interface:

1. Open the website in the browser and confirm that the CMV Summary Audit interface loads properly.

2. Check that the thread list appears on the left side of the page.

3. In the search bar, type a keyword such as:

    - abortion

    - climate

    - democracy

    Then click Search and confirm that the visible threads update.

4. Click on a thread from the list and confirm that the right panel loads the thread details.

5. Check that both the successful and unsuccessful summaries appear for the selected thread.

6. Expand the full thread text and confirm that the source text is displayed.

7. Expand the full summary text and confirm that the full summary content is displayed.

8. Try a few different threads to make sure the interface updates correctly each time.



### Expected behavior

- The page should load without errors.

- The thread list should be visible.

- Search should filter the threads.

- Clicking a thread should display its summaries and full text content.

- The interface should run fully through the browser on localhost.


### Notes

- The corpus is already packaged inside the Docker image, so no extra setup is needed.

- No additional Python packages or local installation steps are required outside of Docker.

