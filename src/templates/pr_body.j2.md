## what

This is an auto-generated PR that updates component `{{ component_name }}` to version `{{ new_version }}`.

| Meta               | Details                                |
|:-------------------|:---------------------------------------|
| **Component**      | `{{ component_name }}`                 |
{% if new_source_name == old_source_name %}
| **Source**         | [{{ old_source_name }}]({{ old_source_link }}) |
{% else %}
| **Old Source**         | [{{ old_source_name }}]({{ old_source_link }}) |
| **New Source**         | [{{ new_source_name }}]({{ new_source_link }}) |
{% endif %}
| **Old Version**    | {% if old_version_link is defined %}[`{{ old_version }}`]({{ old_version_link }}){% else %}`{{ old_version }}`{% endif %}{% if old_component_release_link is defined %}, [Release notes]({{ old_component_release_link }}){% endif %} |
| **New Version**    | {% if new_version_link is defined %}[`{{ new_version }}`]({{ new_version_link }}){% else %}`{{ new_version }}`{% endif %}{% if new_component_release_link is defined %}, [Release notes]({{ new_component_release_link }}){% endif %} |

## why

[Cloud Posse](https://cloudposse.com) recommends upgrading Terraform components regularly to maintain a secure, efficient, and well-supported infrastructure. In doing so, you'll benefit from the latest features, improved compatibility, easier upgrades, and ongoing support while mitigating potential risks and meeting compliance requirements.

- **Enhanced Security**: Updating to the latest version ensures you have the most up-to-date security patches and vulnerability fixes, safeguarding your infrastructure against potential threats.
- **Improved Performance**: Newer versions of Terraform components often come with performance optimizations, enabling your infrastructure to run more efficiently and use resources more effectively.
- **Access to New Features**: Regularly updating ensures access to the latest features and improvements, allowing you to take advantage of new functionality that can help streamline your infrastructure management process.
- **Better Compatibility:** Staying current with Terraform component updates ensures that you maintain compatibility with other components that may also be updating. This can prevent integration issues and ensure smooth operation within your technology stack.
- **Easier Upgrades:** By updating components regularly, you can avoid the challenges of upgrading multiple versions at once, which can be time-consuming and potentially introduce breaking changes. Incremental updates make it easier to identify and resolve issues as they arise.
- **Ongoing Support:** Updated components are more likely to receive continued support from the developer community, including bug fixes, security patches, and new feature development. Falling too far behind can leave your infrastructure unsupported and more vulnerable to issues.
- **Compliance Requirements:** In some cases, regularly updating your Terraform components may be necessary to meet regulatory or industry compliance requirements, ensuring that your infrastructure adheres to specific standards.

## FAQ

### What to do if there are breaking changes?
Please let Cloud Posse know by [raising an issue](https://github.com/cloudposse/terraform-aws-components/issues/new/choose).

### What to do if there are no changes to the deployed infrastructure?
We recommend merging the PR, that way it's easier to identify when there are breaking changes in the future and at what version.

### What to do if there are changes due to the updates?
We recommend carefully reviewing the plan to ensure there's nothing destructive before applying any changes in the automated PRs. If the changes seem reasonable, confirm and deploy. If the changes are unexpected, consider raising an issue.