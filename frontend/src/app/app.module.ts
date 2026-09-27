import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppComponent } from './app.component';
import { LandingLoginComponent } from './components/landing-login/landing-login.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { StepperCreationComponent } from './components/stepper-creation/stepper-creation.component';
import { PipelineProgressComponent } from './components/pipeline-progress/pipeline-progress.component';
import { ContentViewerComponent } from './components/content-viewer/content-viewer.component';
import { InteractiveFlashcardsComponent } from './components/interactive-flashcards/interactive-flashcards.component';
import { InteractiveQuizComponent } from './components/interactive-quiz/interactive-quiz.component';
import { MetadataDashboardComponent } from './components/metadata-dashboard/metadata-dashboard.component';
import { DocumentUploaderComponent } from './components/document-uploader/document-uploader.component';
import { ParameterConfigComponent } from './components/parameter-config/parameter-config.component';

@NgModule({
  declarations: [
    AppComponent,
    LandingLoginComponent,
    DashboardComponent,
    StepperCreationComponent,
    PipelineProgressComponent,
    ContentViewerComponent,
    InteractiveFlashcardsComponent,
    InteractiveQuizComponent,
    MetadataDashboardComponent,
    DocumentUploaderComponent,
    ParameterConfigComponent
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpClientModule
  ],
  providers: [],
  bootstrap: [AppComponent]
})
export class AppModule { }
