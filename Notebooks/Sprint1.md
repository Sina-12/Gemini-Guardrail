# COLX 523 - Advanced Corpus Linguistics

# Sprint 1

## Overall project goal

During this course you will work collaboratively in chosen teams of 3 or 4 to build a corpus with annotation and a web interface. You can choose any internet source of text data from which you can collect a sizable (ideally, at least Brown-sized, i.e. in the order of 1 million words) corpus from within the time frame of Sprint 2 (i.e. the first two weeks of the course). You can choose from the kinds of annotations we have seen so far in this program, or make up your own, as long as it is appropriate to the data and a significant amount of annotation can be collected by Sprint 3 (you are not expected to annotate your entire corpus, you will probably only be able to annotating ~1000 instances.). The web interface will involve allowing some kind of interactive search of your data. Each team will have a mentor (one of the instructors) who meets with the team weekly. 

Note that "instance" might have different meanings - annotating a document for sentiment analysis will result in many more tokens than doing something like anaphor resolution.  In the former, an entire document is an "instance", whereas a single sentence might have several "instances" in the latter.

## Repo setup
rubric={mechanics:2}
- Except for your teamwork report, you will not have individual lab repos for this class. Instead, you will have a single private github repo for your group that you will use for the entire project.  
- First, create such a repo in ubc github (it will be in one of your own repos, not MDS-CL). All the members of your team should have write access, and the primary stakeholders and TA should be given read access (check the syllabus for our github handles). Please message us all on slack with the path to your repo before the first sprint is due.
- Create a branch for each member of your team, where each of you will do your individual work. You should never push directly to the master branch during this project, instead when you are ready to share your work you should create a pull request to master which should be reviewed by one other member of the team.
- You may generally choose how to organize your repo, but you should have documentation on the main repo README that highlights the structure of the repo, and points to where documents and code for each sprint can be found.  It is typical to have separate "src", "data", and "documentation" directories.

## Teamwork contract
rubric={reasoning:2, writing:2}

The first thing you should create (other than the repo) is a teamwork contract. This document will govern your working relationship and if done correctly, should help you manage and resolve any issues that arise.

A teamwork contract communicates specifically how the core group of people will be working together and gives more detail about the logisitics of working together and the expectations you have for each other. Some aspects of the team work contract could be:

- How will work be distributed in a fair and equitable way?
	- We plan on creating a light version of scrum. On Mondays during lunch break, we will have weekly meetings which sets our sprint planning for the week. During these meetings, we first identify the features which needs to be built, and then assess the level of difficulty for each feature. After agreeing to the level of difficulty of each task, we will then distribute responsibilities based on the level of difficulty. In this way, we ensure a fair and equitable way to distribute responsibility. 
- What are the expected work hours for the project? (Not only how many hours, but when do you expect code to be uploaded?)
	- Monday 1 hour. 
	- Tuesday 2 - 5 hour block. 
	- Friday evenings so we have time to review and finalize everything
- How often will group meetings occur?
	- At least two times during the week, plus meetings with stakeholders, as well as extra standups and additional meetings if needed. 
- Will you have meeting agendas and minutes?  If so, who keeps track of them?  Where are they stored?
	- At the end of Monday meetings scrum leader writes down minutes
- What will be the style of working?  Do you schedule hackathons, or do you set deadlines that teammates need to meet?
	- both structured and flexible. we will have deadlines but only to progress our tasks. 
	- one short meeting, one longer hackathon
	- communicate about time spent on each project
- Will you use daily "stand-ups", or submit written summaries of your contributions, or something else?

- What is the quality of work each team member expects from themselves and each other?
- When are team members not available (e.g., evenings and Sundays because of family obligations).
- Who will be scrum leader each week?  The scrum leader is responsible for making sure everyone contributes to their week's deliverable, and makes sure work is distributed equally.
	- second week Rayan
	- third week Jai
	- Fourth week Sina
	- Five week Gilly
- Is there any behaviour you wish to highlight as being expected or unacceptable (i.e., what is the code of conduct for the group?)
	- respond promptly
	- if you dont manage task let people know ahead of time
- How do you do code review?  Do you pair up, and always review the same person's code, or do you rotate weekly?
	- in our meeting we can do it collaboratively
	- we will assign code review as a task
- And any other similar things that govern your working relationships.

Furthermore, each member of the team needs to do a self-reflection and rank their skills (out of 5) for each of the following:

* Communicative - communication is all about knowing what is expected for each sprint, and making sure that the team is progressing towards those goals
	* Sina: 5
	* Rayan: 3
	* Gilly: 4
* Analytical - analysts take a larger view of the project, and plan around future needs of the team
	* Rayan: 5
	* Sina: 4
	* Gilly: 2
* Creative - creators have lots of great ideas that can produce inspiration about where a project needs to go
	* Rayan: 5
	* Sina: 4
	* Gilly: 5
	* Jai: 1
* Synergistic - Synergists can put together the different parts of a project to make something more than its parts.  They work with people with other styles to create a cohesive whole.  After analyzing your skillset, please discuss it with your teammates, and use this information to inform your project.  Include the self reflection in the repo.
	* Rayan: 5
	* Sina: 4
	* Gilly: 3

Use this opportunity to apply your prior knowledge/experience to improve your teamwork, communication, leadership, and organizational skills. For this and all other written work in this course, do pay attention to the basic mechanics of writing, including spelling and grammar (everyone in the team should read over all the documents looking for such errors).  Keep in mind that some teams have members with leadership experience - take advantage of it!


## Project proposal
rubric={reasoning:5,writing:2}

Describe the corpus you intend to build. You should include the following information and anything else you deem relevant:

- What is the exact source of the data? You should include a link to the website.  You are allowed (and encouraged) to find and download an existing corpus, but you must also build a scraper (see Sprint 2).
	- We will be using argumants from Reddit and other sources, mainly focusong on tezt that is persuasive, and uses language that is highly opinionated
- What kind of text is it? What language is it in? What is the genre/register? What are the texts about? Who wrote them? How long are the documents, generally?                                                    
- Will you be targeting a specific kind of text among those available on the site? If so, how will you be filtering the texts to just the kind you want? Is there enough data there to create a "Brown-sized" corpus? (Note, if you really like your corpus idea but it falls far short of "Brown-sized", discuss it with your mentor before your project proposal)
- Is there any structure to the corpus you are building (e.g. discussion threads)? Any metadata (e.g. related to author identity)?
- What do you have in mind for your annotation of this corpus? (this does not have to be your final choice of annotation, but you should have an idea before you start collecting data)
- In what format are you going to store the corpus and any associated metadata? (JSON? txt? Database?)  
- What makes this corpus potentially of interest? What could it be used for? (Think broadly a lot of corpora have secondary uses beyond the primary annotation.)

## Compelling proposal (Optional)
rubric={raw:2}

You can get bonus points in this sprint by having a particularly compelling proposal, one which, for instance, has the potential to answer research questions, service an under-resourced language or group, or otherwise be applied usefully beyond this course (training data for an important task, for instance). Projects done in languages other than English, using less obvious sources of data, and involving synergy between annotation and metadata are more likely to get these bonus points. Discussing similar corpora that are available might be useful to convince us that your corpus is going to be something special.
                          

## Corpus collection POC (proof-of-concept)
rubric={accuracy:2,reasoning:2,writing:1}

You need to demonstrate that you will be able to collect the corpus you have proposed. You don't have to have a complete scraper for this sprint, but you must have the following:

- Pyhon code that downloads one document. Make sure that this code is setup to be runnable, because we will run it. Please provide explict explanation on how to use it, assuming someone has cloned your repo. It must be a .py script - no notebooks in this course.  You are allowed to provide notebooks to demonstrate graphs, etc., but if your main script is a notebook for any sprint, it will not be accepted, and you will be required to reconfigure it as a .py file.
- A step-by-step algorithm for creating the corpus (similar to the one for web scraping tutorial we are doing this week). If appropriate, include links to the website or API documentation for functions you are using. Write as clearly as possible.


## Prompt completion
rubric={raw:4}

You should finish everything discussed above by 11:59pm Saturday, Feb 21th. If you were not able to complete it on time you will lose 1 point from your timely completion score for each 12 hour period after the deadline. When you are done with a sprint (regardless of whether you are on time or late), your scrum leader MUST open an issue in your repo that says you are done. Any modification of the relevant documents in your repo after you have opened this issue will likely result in losing all your prompt completion points.

A prompt completion grade of 0 (ie, a submission more than 2 days late or code modification after the deadline) will also result in a 50% penalty for the entire sprint.
