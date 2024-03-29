## 1.1 Pipeline Configuration Overview

### 1.1.1 Description

The pipeline configuration includes several key components designed to enhance functionality, manage dependencies, and streamline processes. Each component plays a crucial role in ensuring the smooth execution of the pipeline.

### 1.1.2 Included Configuration Files

The pipeline configuration leverages modularization by including various configuration files from a centralized location. These files contribute to different aspects of the pipeline:

[SJI-1010]

1. **Show Dependencies**
 - Provides transparency into project dependencies.
 - Configuration file: [.show-dependencies.yml](https://xxxxxx.yml)

```mermaid
graph TD;
    A-->B;
    A-->C;
    B-->D;
    C-->D;
```

https://dirtyagil.atlassian.net/browse/AD-120

https://dirtyagile.atlassian.net/browse/AD-121
